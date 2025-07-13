"""
Receipt parsing service for extracting grocery items from email receipts
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class ReceiptParser:
    """Parse grocery receipts from various stores"""

    # Common patterns for grocery items
    QUANTITY_PATTERNS = [
        r"(\d+\.?\d*)\s*x\s*(.+?)(?:\s+\$?[\d.,]+)?$",  # "2 x Milk $6.99"
        r"(\d+\.?\d*)\s+(.+?)(?:\s+\$?[\d.,]+)?$",  # "2 Milk $6.99"
        r"(.+?)\s+qty:?\s*(\d+\.?\d*)",  # "Milk qty: 2"
        r"(.+?)\s+\((\d+\.?\d*)\)",  # "Milk (2)"
    ]

    PRICE_PATTERN = r"\$?(\d+\.?\d*)"

    # Store-specific configurations
    STORE_CONFIGS = {
        "instacart": {
            "sender_patterns": [r".*@instacart\.com", r".*instacart.*"],
            "item_patterns": [
                r"^(\d+\.?\d*)\s*x\s*(.+?)\s*\$?([\d.,]+)$",
                r"^(.+?)\s*\$?([\d.,]+)$",
            ],
            "skip_patterns": [
                r"subtotal",
                r"tax",
                r"tip",
                r"delivery",
                r"service fee",
                r"total",
                r"discount",
                r"coupon",
                r"promo",
            ],
            "date_patterns": [r"delivered on (.+)", r"order placed (.+)"],
        },
        "amazon_fresh": {
            "sender_patterns": [r".*@amazon\.com", r".*amazonfresh.*"],
            "item_patterns": [
                r"^(.+?)\s*\$?([\d.,]+)$",
                r"^(\d+\.?\d*)\s*x\s*(.+?)\s*\$?([\d.,]+)$",
            ],
            "skip_patterns": [
                r"subtotal",
                r"tax",
                r"total",
                r"shipping",
                r"prime",
                r"discount",
                r"promotion",
                r"credit",
            ],
            "date_patterns": [r"delivered (.+)", r"order date (.+)"],
        },
        "walmart": {
            "sender_patterns": [r".*@walmart\.com", r".*walmart.*"],
            "item_patterns": [
                r"^(.+?)\s*\$?([\d.,]+)$",
                r"^(\d+\.?\d*)\s+(.+?)\s*\$?([\d.,]+)$",
            ],
            "skip_patterns": [
                r"subtotal",
                r"tax",
                r"total",
                r"savings",
                r"pickup",
                r"discount",
                r"coupon",
            ],
            "date_patterns": [r"pickup date (.+)", r"order date (.+)"],
        },
        "target": {
            "sender_patterns": [r".*@target\.com", r".*target.*"],
            "item_patterns": [r"^(.+?)\s*\$?([\d.,]+)$"],
            "skip_patterns": [
                r"subtotal",
                r"tax",
                r"total",
                r"redcard",
                r"circle",
                r"discount",
                r"promotion",
            ],
            "date_patterns": [r"order date (.+)"],
        },
    }

    def __init__(self):
        self.store_config = None

    def detect_store(self, sender_email: str, subject: str, body: str) -> Optional[str]:
        """Detect which store the receipt is from"""
        sender_lower = sender_email.lower()
        subject_lower = subject.lower()
        body_lower = body.lower()

        for store, config in self.STORE_CONFIGS.items():
            # Check sender patterns
            for pattern in config["sender_patterns"]:
                if re.search(pattern, sender_lower):
                    return store

            # Check subject/body for store names
            if (
                store.replace("_", " ") in subject_lower
                or store.replace("_", " ") in body_lower
            ):
                return store

        return None

    def parse_receipt(self, email_data: Dict) -> Dict:
        """Parse a receipt email and extract items"""
        sender = email_data.get("sender", "")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")

        # Detect store
        store = self.detect_store(sender, subject, body)
        if store:
            self.store_config = self.STORE_CONFIGS[store]
        else:
            # Use generic parsing
            self.store_config = None

        # Extract basic info
        receipt_data = {
            "store": store or "unknown",
            "sender": sender,
            "subject": subject,
            "purchase_date": self._extract_date(body),
            "items": [],
            "total_amount": self._extract_total(body),
            "confidence_score": 0.0,
        }

        # Parse items
        items = self._parse_items(body)
        receipt_data["items"] = items
        receipt_data["confidence_score"] = self._calculate_confidence(items, body)

        return receipt_data

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract purchase date from receipt text"""
        if not self.store_config:
            # Generic date patterns
            date_patterns = [
                r"(\d{1,2}/\d{1,2}/\d{4})",
                r"(\d{4}-\d{2}-\d{2})",
                r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}",
                r"(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4})",
            ]
        else:
            date_patterns = self.store_config.get("date_patterns", [])

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_total(self, text: str) -> Optional[Decimal]:
        """Extract total amount from receipt"""
        # Look for total lines
        total_patterns = [
            r"total:?\s*\$?([\d.,]+)",
            r"amount:?\s*\$?([\d.,]+)",
            r"grand total:?\s*\$?([\d.,]+)",
        ]

        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return Decimal(match.group(1).replace(",", ""))
                except InvalidOperation:
                    continue

        return None

    def _parse_items(self, text: str) -> List[Dict]:
        """Parse individual items from receipt text"""
        items = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Skip common non-item lines
            if self._should_skip_line(line):
                continue

            # Try to parse as item
            item = self._parse_item_line(line, i)
            if item:
                items.append(item)

        return items

    def _should_skip_line(self, line: str) -> bool:
        """Check if line should be skipped"""
        line_lower = line.lower()

        # Common skip patterns
        skip_patterns = [
            r"^\s*$",  # Empty lines
            r"^\s*[-=_]{3,}",  # Separator lines
            r"thank you",
            r"receipt",
            r"order #",
            r"transaction",
            r"customer",
            r"cashier",
            r"store",
            r"address",
            r"phone",
            r"email",
            r"website",
            r"survey",
        ]

        # Store-specific skip patterns
        if self.store_config:
            skip_patterns.extend(self.store_config.get("skip_patterns", []))

        for pattern in skip_patterns:
            if re.search(pattern, line_lower):
                return True

        return False

    def _parse_item_line(self, line: str, line_number: int) -> Optional[Dict]:
        """Parse a single line as a grocery item"""
        line = line.strip()

        # Try store-specific patterns first
        if self.store_config:
            patterns = self.store_config.get("item_patterns", [])
        else:
            patterns = [
                r"^(\d+\.?\d*)\s*x\s*(.+?)\s*\$?([\d.,]+)$",  # "2 x Milk $6.99"
                r"^(.+?)\s*\$?([\d.,]+)$",  # "Milk $6.99"
            ]

        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return self._extract_item_from_match(match, line, line_number)

        # Try generic quantity patterns
        for pattern in self.QUANTITY_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return self._extract_item_from_match(match, line, line_number)

        return None

    def _extract_item_from_match(self, match, line: str, line_number: int) -> Dict:
        """Extract item data from regex match"""
        groups = match.groups()

        # Determine quantity, name, and price based on match groups
        if len(groups) == 3:
            # Pattern: quantity, name, price or name, quantity, price
            if re.match(r"^\d+\.?\d*$", groups[0]):
                quantity, name, price = groups
            else:
                name, quantity, price = groups
        elif len(groups) == 2:
            # Pattern: name, price or quantity, name
            if re.match(r"^\d+\.?\d*$", groups[0]):
                quantity, name = groups
                price = None
            else:
                name, price = groups
                quantity = "1"
        else:
            # Single group - assume it's the name
            name = groups[0]
            quantity = "1"
            price = None

        # Clean and validate data
        name = self._clean_item_name(name)
        quantity = self._parse_quantity(quantity)
        price = self._parse_price(price) if price else None

        # Calculate confidence
        confidence = self._calculate_item_confidence(name, quantity, price, line)

        return {
            "name": name,
            "quantity": float(quantity),
            "unit": self._detect_unit(name),
            "price": float(price) if price else None,
            "raw_text": line,
            "line_number": line_number,
            "confidence_score": confidence,
        }

    def _clean_item_name(self, name: str) -> str:
        """Clean item name"""
        # Remove common prefixes/suffixes
        name = re.sub(r"^\d+\.?\d*\s*x\s*", "", name, flags=re.IGNORECASE)
        name = re.sub(r"\s*\$?[\d.,]+$", "", name)
        name = re.sub(r"\s*\(.*?\)$", "", name)  # Remove parenthetical info

        # Clean whitespace and special characters
        name = re.sub(r"\s+", " ", name).strip()

        return name

    def _parse_quantity(self, quantity_str: str) -> Decimal:
        """Parse quantity string to decimal"""
        if isinstance(quantity_str, str):
            # Remove non-numeric characters except decimal point
            clean_qty = re.sub(r"[^\d.]", "", quantity_str)
            try:
                return Decimal(clean_qty) if clean_qty else Decimal("1")
            except InvalidOperation:
                return Decimal("1")
        return Decimal("1")

    def _parse_price(self, price_str: str) -> Optional[Decimal]:
        """Parse price string to decimal"""
        if not price_str:
            return None

        # Remove currency symbols and spaces
        clean_price = re.sub(r"[^\d.,]", "", price_str)
        clean_price = clean_price.replace(",", "")

        try:
            return Decimal(clean_price)
        except InvalidOperation:
            return None

    def _detect_unit(self, name: str) -> str:
        """Detect unit from item name"""
        name_lower = name.lower()

        # Common units
        unit_patterns = [
            (r"\b(\d+\.?\d*)\s*(oz|ounce|ounces)\b", "oz"),
            (r"\b(\d+\.?\d*)\s*(lb|lbs|pound|pounds)\b", "lb"),
            (r"\b(\d+\.?\d*)\s*(gal|gallon|gallons)\b", "gal"),
            (r"\b(\d+\.?\d*)\s*(qt|quart|quarts)\b", "qt"),
            (r"\b(\d+\.?\d*)\s*(pt|pint|pints)\b", "pt"),
            (r"\b(\d+\.?\d*)\s*(fl oz|fluid ounce)\b", "fl oz"),
            (r"\b(\d+\.?\d*)\s*(ml|milliliter)\b", "ml"),
            (r"\b(\d+\.?\d*)\s*(l|liter|litre)\b", "l"),
            (r"\b(pack|package|pkg)\b", "pack"),
            (r"\b(bag|bags)\b", "bag"),
            (r"\b(box|boxes)\b", "box"),
            (r"\b(bottle|bottles)\b", "bottle"),
            (r"\b(can|cans)\b", "can"),
        ]

        for pattern, unit in unit_patterns:
            if re.search(pattern, name_lower):
                return unit

        return "item"

    def _calculate_item_confidence(
        self, name: str, quantity: Decimal, price: Optional[Decimal], raw_text: str
    ) -> float:
        """Calculate confidence score for parsed item"""
        score = 0.0

        # Name quality (40% of score)
        if name and len(name) > 2:
            score += 0.4
            if len(name) > 5:
                score += 0.1
            if not re.search(r"\d+", name):  # No random numbers
                score += 0.1

        # Quantity parsing (20% of score)
        if quantity and quantity > 0:
            score += 0.2

        # Price parsing (20% of score)
        if price and price > 0:
            score += 0.2

        # Line structure (20% of score)
        if re.search(r"\$", raw_text):  # Has price indicator
            score += 0.1
        if re.search(r"\d+\.?\d*\s*x\s*", raw_text):  # Has quantity indicator
            score += 0.1

        return min(score, 1.0)

    def _calculate_confidence(self, items: List[Dict], text: str) -> float:
        """Calculate overall confidence score for receipt parsing"""
        if not items:
            return 0.0

        # Average item confidence
        item_scores = [item.get("confidence_score", 0) for item in items]
        avg_item_score = sum(item_scores) / len(item_scores)

        # Structure indicators
        structure_score = 0.0
        if re.search(r"total", text, re.IGNORECASE):
            structure_score += 0.3
        if re.search(r"tax", text, re.IGNORECASE):
            structure_score += 0.2
        if re.search(r"\$[\d.,]+", text):  # Has prices
            structure_score += 0.3
        if len(items) >= 3:  # Reasonable number of items
            structure_score += 0.2

        # Weighted average
        final_score = (avg_item_score * 0.7) + (structure_score * 0.3)
        return min(final_score, 1.0)
