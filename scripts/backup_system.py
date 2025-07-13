#!/usr/bin/env python3
"""
Comprehensive backup system for Kitchentory.
Handles database backups, media files, and configuration.
"""

import os
import sys
import argparse
import logging
import datetime
import subprocess
import shutil
import tarfile
import gzip
import boto3
import psycopg2
from pathlib import Path
from typing import List, Dict, Optional
import json
import hashlib


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/opt/kitchentory/logs/backup.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class BackupConfig:
    """Configuration for backup operations."""

    def __init__(self):
        self.backup_dir = Path(os.getenv("BACKUP_DIR", "/opt/kitchentory/backups"))
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_name = os.getenv("DB_NAME", "kitchentory")
        self.db_user = os.getenv("DB_USER", "kitchentory")
        self.db_password = os.getenv("DB_PASSWORD")
        self.media_dir = Path(os.getenv("MEDIA_ROOT", "/opt/kitchentory/media"))
        self.static_dir = Path(os.getenv("STATIC_ROOT", "/opt/kitchentory/static"))

        # Retention settings
        self.daily_retention = int(os.getenv("BACKUP_DAILY_RETENTION", "7"))
        self.weekly_retention = int(os.getenv("BACKUP_WEEKLY_RETENTION", "4"))
        self.monthly_retention = int(os.getenv("BACKUP_MONTHLY_RETENTION", "12"))

        # AWS S3 settings (optional)
        self.s3_bucket = os.getenv("BACKUP_S3_BUCKET")
        self.s3_region = os.getenv("BACKUP_S3_REGION", "us-east-1")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        # Encryption settings
        self.encryption_key = os.getenv("BACKUP_ENCRYPTION_KEY")

        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)


class DatabaseBackup:
    """Handle database backup operations."""

    def __init__(self, config: BackupConfig):
        self.config = config

    def create_backup(self, backup_name: str) -> Path:
        """Create a database backup."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.config.backup_dir / f"db_{backup_name}_{timestamp}.sql"
        compressed_file = backup_file.with_suffix(".sql.gz")

        try:
            logger.info(f"Creating database backup: {compressed_file}")

            # Create environment for pg_dump
            env = os.environ.copy()
            if self.config.db_password:
                env["PGPASSWORD"] = self.config.db_password

            # Run pg_dump
            cmd = [
                "pg_dump",
                "-h",
                self.config.db_host,
                "-U",
                self.config.db_user,
                "-d",
                self.config.db_name,
                "--no-password",
                "--verbose",
                "--clean",
                "--if-exists",
                "--create",
            ]

            with open(backup_file, "w") as f:
                result = subprocess.run(
                    cmd, stdout=f, stderr=subprocess.PIPE, env=env, text=True
                )

            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")

            # Compress the backup
            with open(backup_file, "rb") as f_in:
                with gzip.open(compressed_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Remove uncompressed file
            backup_file.unlink()

            # Calculate checksum
            checksum = self._calculate_checksum(compressed_file)
            checksum_file = compressed_file.with_suffix(".sql.gz.sha256")
            checksum_file.write_text(f"{checksum}  {compressed_file.name}\n")

            logger.info(f"Database backup completed: {compressed_file}")
            return compressed_file

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            # Clean up partial files
            for f in [backup_file, compressed_file]:
                if f.exists():
                    f.unlink()
            raise

    def restore_backup(self, backup_file: Path) -> bool:
        """Restore database from backup."""
        try:
            logger.info(f"Restoring database from: {backup_file}")

            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")

            # Verify checksum if available
            checksum_file = backup_file.with_suffix(".sql.gz.sha256")
            if checksum_file.exists():
                if not self._verify_checksum(backup_file, checksum_file):
                    raise Exception("Backup file checksum verification failed")

            # Create environment for psql
            env = os.environ.copy()
            if self.config.db_password:
                env["PGPASSWORD"] = self.config.db_password

            # Restore database
            cmd = ["gunzip", "-c", str(backup_file)]

            psql_cmd = [
                "psql",
                "-h",
                self.config.db_host,
                "-U",
                self.config.db_user,
                "-d",
                "postgres",  # Connect to postgres db first
                "--no-password",
            ]

            # Decompress and restore
            gunzip_process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            psql_process = subprocess.run(
                psql_cmd,
                stdin=gunzip_process.stdout,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
            )

            gunzip_process.wait()

            if psql_process.returncode != 0:
                raise Exception(f"Database restore failed: {psql_process.stderr}")

            logger.info("Database restore completed successfully")
            return True

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _verify_checksum(self, file_path: Path, checksum_file: Path) -> bool:
        """Verify file checksum."""
        actual_checksum = self._calculate_checksum(file_path)
        expected_checksum = checksum_file.read_text().split()[0]
        return actual_checksum == expected_checksum


class MediaBackup:
    """Handle media files backup operations."""

    def __init__(self, config: BackupConfig):
        self.config = config

    def create_backup(self, backup_name: str) -> Path:
        """Create a media files backup."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.config.backup_dir / f"media_{backup_name}_{timestamp}.tar.gz"

        try:
            logger.info(f"Creating media backup: {backup_file}")

            if not self.config.media_dir.exists():
                logger.warning(
                    f"Media directory does not exist: {self.config.media_dir}"
                )
                return None

            # Create tar.gz archive
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(self.config.media_dir, arcname="media", recursive=True)

            # Calculate checksum
            checksum = self._calculate_checksum(backup_file)
            checksum_file = backup_file.with_suffix(".tar.gz.sha256")
            checksum_file.write_text(f"{checksum}  {backup_file.name}\n")

            logger.info(f"Media backup completed: {backup_file}")
            return backup_file

        except Exception as e:
            logger.error(f"Media backup failed: {e}")
            if backup_file.exists():
                backup_file.unlink()
            raise

    def restore_backup(
        self, backup_file: Path, restore_dir: Optional[Path] = None
    ) -> bool:
        """Restore media files from backup."""
        try:
            restore_path = restore_dir or self.config.media_dir.parent
            logger.info(f"Restoring media from: {backup_file} to {restore_path}")

            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")

            # Verify checksum if available
            checksum_file = backup_file.with_suffix(".tar.gz.sha256")
            if checksum_file.exists():
                if not self._verify_checksum(backup_file, checksum_file):
                    raise Exception("Backup file checksum verification failed")

            # Extract archive
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(path=restore_path)

            logger.info("Media restore completed successfully")
            return True

        except Exception as e:
            logger.error(f"Media restore failed: {e}")
            return False

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _verify_checksum(self, file_path: Path, checksum_file: Path) -> bool:
        """Verify file checksum."""
        actual_checksum = self._calculate_checksum(file_path)
        expected_checksum = checksum_file.read_text().split()[0]
        return actual_checksum == expected_checksum


class ConfigBackup:
    """Handle configuration files backup."""

    def __init__(self, config: BackupConfig):
        self.config = config
        self.config_files = [
            "/opt/kitchentory/app/.env",
            "/etc/nginx/sites-available/kitchentory",
            "/etc/supervisor/conf.d/kitchentory.conf",
            "/etc/postgresql/*/main/postgresql.conf",
            "/etc/redis/redis.conf",
        ]

    def create_backup(self, backup_name: str) -> Path:
        """Create configuration backup."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = (
            self.config.backup_dir / f"config_{backup_name}_{timestamp}.tar.gz"
        )

        try:
            logger.info(f"Creating configuration backup: {backup_file}")

            with tarfile.open(backup_file, "w:gz") as tar:
                for config_file in self.config_files:
                    # Handle glob patterns
                    if "*" in config_file:
                        import glob

                        for file_path in glob.glob(config_file):
                            if os.path.exists(file_path):
                                tar.add(file_path, arcname=file_path.replace("/", "_"))
                    else:
                        if os.path.exists(config_file):
                            tar.add(config_file, arcname=config_file.replace("/", "_"))

            logger.info(f"Configuration backup completed: {backup_file}")
            return backup_file

        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            if backup_file.exists():
                backup_file.unlink()
            raise


class S3BackupStorage:
    """Handle S3 backup storage operations."""

    def __init__(self, config: BackupConfig):
        self.config = config
        self.s3_client = None

        if self.config.s3_bucket:
            self.s3_client = boto3.client(
                "s3",
                region_name=self.config.s3_region,
                aws_access_key_id=self.config.aws_access_key,
                aws_secret_access_key=self.config.aws_secret_key,
            )

    def upload_backup(self, local_file: Path, s3_key: str = None) -> bool:
        """Upload backup file to S3."""
        if not self.s3_client:
            logger.warning("S3 not configured, skipping upload")
            return False

        try:
            s3_key = s3_key or f"backups/{local_file.name}"
            logger.info(
                f"Uploading {local_file} to s3://{self.config.s3_bucket}/{s3_key}"
            )

            self.s3_client.upload_file(
                str(local_file),
                self.config.s3_bucket,
                s3_key,
                ExtraArgs={
                    "StorageClass": "STANDARD_IA",  # Infrequent Access
                    "ServerSideEncryption": "AES256",
                },
            )

            logger.info(f"Successfully uploaded to S3: {s3_key}")
            return True

        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def download_backup(self, s3_key: str, local_file: Path) -> bool:
        """Download backup file from S3."""
        if not self.s3_client:
            logger.error("S3 not configured")
            return False

        try:
            logger.info(
                f"Downloading s3://{self.config.s3_bucket}/{s3_key} to {local_file}"
            )

            self.s3_client.download_file(self.config.s3_bucket, s3_key, str(local_file))

            logger.info(f"Successfully downloaded from S3: {s3_key}")
            return True

        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            return False

    def list_backups(self, prefix: str = "backups/") -> List[Dict]:
        """List backup files in S3."""
        if not self.s3_client:
            return []

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.s3_bucket, Prefix=prefix
            )

            return response.get("Contents", [])

        except Exception as e:
            logger.error(f"Failed to list S3 backups: {e}")
            return []


class BackupRetentionManager:
    """Manage backup retention policies."""

    def __init__(self, config: BackupConfig):
        self.config = config

    def cleanup_old_backups(self):
        """Remove old backups based on retention policy."""
        logger.info("Starting backup cleanup")

        backup_files = list(self.config.backup_dir.glob("*.gz"))
        backup_files.extend(list(self.config.backup_dir.glob("*.tar.gz")))

        # Group backups by type and date
        backups_by_type = {}
        for backup_file in backup_files:
            backup_type = self._get_backup_type(backup_file)
            backup_date = self._get_backup_date(backup_file)

            if backup_type and backup_date:
                if backup_type not in backups_by_type:
                    backups_by_type[backup_type] = []
                backups_by_type[backup_type].append((backup_date, backup_file))

        # Apply retention policy for each type
        for backup_type, backups in backups_by_type.items():
            backups.sort(key=lambda x: x[0], reverse=True)  # Newest first
            self._apply_retention_policy(backup_type, backups)

    def _get_backup_type(self, backup_file: Path) -> Optional[str]:
        """Extract backup type from filename."""
        name = backup_file.name
        if name.startswith("db_"):
            return "database"
        elif name.startswith("media_"):
            return "media"
        elif name.startswith("config_"):
            return "config"
        return None

    def _get_backup_date(self, backup_file: Path) -> Optional[datetime.datetime]:
        """Extract backup date from filename."""
        try:
            # Extract timestamp from filename (format: YYYYMMDD_HHMMSS)
            parts = backup_file.stem.split("_")
            for part in parts:
                if len(part) == 15 and part[8] == "_":  # YYYYMMDD_HHMMSS
                    return datetime.datetime.strptime(part, "%Y%m%d_%H%M%S")
        except:
            pass
        return None

    def _apply_retention_policy(self, backup_type: str, backups: List):
        """Apply retention policy to backups."""
        now = datetime.datetime.now()

        daily_kept = 0
        weekly_kept = 0
        monthly_kept = 0

        for backup_date, backup_file in backups:
            age_days = (now - backup_date).days

            keep_backup = False

            # Keep daily backups
            if (
                age_days <= self.config.daily_retention
                and daily_kept < self.config.daily_retention
            ):
                keep_backup = True
                daily_kept += 1

            # Keep weekly backups (one per week)
            elif (
                age_days <= 30
                and backup_date.weekday() == 6
                and weekly_kept < self.config.weekly_retention
            ):
                keep_backup = True
                weekly_kept += 1

            # Keep monthly backups (one per month, on first Sunday)
            elif (
                backup_date.day <= 7
                and backup_date.weekday() == 6
                and monthly_kept < self.config.monthly_retention
            ):
                keep_backup = True
                monthly_kept += 1

            if not keep_backup:
                logger.info(f"Removing old backup: {backup_file}")
                backup_file.unlink(missing_ok=True)

                # Remove checksum file if exists
                checksum_file = backup_file.with_suffix(backup_file.suffix + ".sha256")
                checksum_file.unlink(missing_ok=True)


class BackupManager:
    """Main backup management class."""

    def __init__(self):
        self.config = BackupConfig()
        self.db_backup = DatabaseBackup(self.config)
        self.media_backup = MediaBackup(self.config)
        self.config_backup = ConfigBackup(self.config)
        self.s3_storage = S3BackupStorage(self.config)
        self.retention_manager = BackupRetentionManager(self.config)

    def create_full_backup(self, backup_name: str = None) -> Dict[str, Path]:
        """Create a full backup (database + media + config)."""
        if not backup_name:
            backup_name = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        backups = {}

        try:
            logger.info(f"Starting full backup: {backup_name}")

            # Database backup
            db_backup_file = self.db_backup.create_backup(backup_name)
            if db_backup_file:
                backups["database"] = db_backup_file
                if self.config.s3_bucket:
                    self.s3_storage.upload_backup(db_backup_file)

            # Media backup
            media_backup_file = self.media_backup.create_backup(backup_name)
            if media_backup_file:
                backups["media"] = media_backup_file
                if self.config.s3_bucket:
                    self.s3_storage.upload_backup(media_backup_file)

            # Configuration backup
            config_backup_file = self.config_backup.create_backup(backup_name)
            if config_backup_file:
                backups["config"] = config_backup_file
                if self.config.s3_bucket:
                    self.s3_storage.upload_backup(config_backup_file)

            # Create backup manifest
            manifest = self._create_backup_manifest(backup_name, backups)
            manifest_file = self.config.backup_dir / f"manifest_{backup_name}.json"
            manifest_file.write_text(json.dumps(manifest, indent=2, default=str))

            logger.info(f"Full backup completed: {backup_name}")
            return backups

        except Exception as e:
            logger.error(f"Full backup failed: {e}")
            raise

    def restore_full_backup(self, backup_name: str) -> bool:
        """Restore from a full backup."""
        try:
            logger.info(f"Starting full restore: {backup_name}")

            # Find backup files
            manifest_file = self.config.backup_dir / f"manifest_{backup_name}.json"
            if manifest_file.exists():
                manifest = json.loads(manifest_file.read_text())
                backup_files = manifest.get("files", {})
            else:
                # Find files by pattern
                backup_files = self._find_backup_files(backup_name)

            success = True

            # Restore database
            if "database" in backup_files:
                db_file = Path(backup_files["database"])
                if not self.db_backup.restore_backup(db_file):
                    success = False

            # Restore media
            if "media" in backup_files:
                media_file = Path(backup_files["media"])
                if not self.media_backup.restore_backup(media_file):
                    success = False

            if success:
                logger.info(f"Full restore completed: {backup_name}")
            else:
                logger.error(f"Full restore failed: {backup_name}")

            return success

        except Exception as e:
            logger.error(f"Full restore failed: {e}")
            return False

    def list_backups(self) -> List[Dict]:
        """List available backups."""
        backups = []

        # Local backups
        manifest_files = list(self.config.backup_dir.glob("manifest_*.json"))
        for manifest_file in manifest_files:
            try:
                manifest = json.loads(manifest_file.read_text())
                backups.append(
                    {
                        "name": manifest["name"],
                        "date": manifest["date"],
                        "location": "local",
                        "files": manifest["files"],
                    }
                )
            except:
                pass

        # S3 backups
        s3_backups = self.s3_storage.list_backups()
        for s3_backup in s3_backups:
            if s3_backup["Key"].endswith("manifest.json"):
                backups.append(
                    {
                        "name": s3_backup["Key"],
                        "date": s3_backup["LastModified"],
                        "location": "s3",
                        "size": s3_backup["Size"],
                    }
                )

        return sorted(backups, key=lambda x: x["date"], reverse=True)

    def cleanup_backups(self):
        """Clean up old backups."""
        self.retention_manager.cleanup_old_backups()

    def _create_backup_manifest(
        self, backup_name: str, backups: Dict[str, Path]
    ) -> Dict:
        """Create backup manifest."""
        return {
            "name": backup_name,
            "date": datetime.datetime.now().isoformat(),
            "version": "1.0",
            "files": {k: str(v) for k, v in backups.items()},
            "checksums": {k: self._calculate_checksum(v) for k, v in backups.items()},
        }

    def _find_backup_files(self, backup_name: str) -> Dict[str, str]:
        """Find backup files by pattern."""
        files = {}

        # Database backup
        db_files = list(self.config.backup_dir.glob(f"db_{backup_name}_*.sql.gz"))
        if db_files:
            files["database"] = str(db_files[0])

        # Media backup
        media_files = list(self.config.backup_dir.glob(f"media_{backup_name}_*.tar.gz"))
        if media_files:
            files["media"] = str(media_files[0])

        # Config backup
        config_files = list(
            self.config.backup_dir.glob(f"config_{backup_name}_*.tar.gz")
        )
        if config_files:
            files["config"] = str(config_files[0])

        return files

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate file checksum."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Kitchentory Backup System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create backup
    create_parser = subparsers.add_parser("create", help="Create backup")
    create_parser.add_argument("--name", help="Backup name")
    create_parser.add_argument(
        "--type",
        choices=["full", "database", "media", "config"],
        default="full",
        help="Backup type",
    )

    # Restore backup
    restore_parser = subparsers.add_parser("restore", help="Restore backup")
    restore_parser.add_argument("name", help="Backup name to restore")
    restore_parser.add_argument(
        "--type",
        choices=["full", "database", "media"],
        default="full",
        help="Restore type",
    )

    # List backups
    list_parser = subparsers.add_parser("list", help="List backups")

    # Cleanup backups
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup old backups")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    backup_manager = BackupManager()

    try:
        if args.command == "create":
            if args.type == "full":
                backups = backup_manager.create_full_backup(args.name)
                print(f"Created backups: {backups}")
            elif args.type == "database":
                backup_file = backup_manager.db_backup.create_backup(
                    args.name or "manual"
                )
                print(f"Created database backup: {backup_file}")
            elif args.type == "media":
                backup_file = backup_manager.media_backup.create_backup(
                    args.name or "manual"
                )
                print(f"Created media backup: {backup_file}")
            elif args.type == "config":
                backup_file = backup_manager.config_backup.create_backup(
                    args.name or "manual"
                )
                print(f"Created config backup: {backup_file}")

        elif args.command == "restore":
            if args.type == "full":
                success = backup_manager.restore_full_backup(args.name)
                print(f"Restore {'successful' if success else 'failed'}")
            elif args.type == "database":
                backup_files = backup_manager._find_backup_files(args.name)
                if "database" in backup_files:
                    success = backup_manager.db_backup.restore_backup(
                        Path(backup_files["database"])
                    )
                    print(f"Database restore {'successful' if success else 'failed'}")
                else:
                    print(f"Database backup not found for: {args.name}")

        elif args.command == "list":
            backups = backup_manager.list_backups()
            print(f"{'Name':<30} {'Date':<20} {'Location':<10}")
            print("-" * 60)
            for backup in backups:
                date_str = (
                    backup["date"][:19]
                    if isinstance(backup["date"], str)
                    else str(backup["date"])[:19]
                )
                print(f"{backup['name']:<30} {date_str:<20} {backup['location']:<10}")

        elif args.command == "cleanup":
            backup_manager.cleanup_backups()
            print("Backup cleanup completed")

    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
