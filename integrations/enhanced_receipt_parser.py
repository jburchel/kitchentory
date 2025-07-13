"""
Enhanced Receipt Parser for Email Receipts
Supports major grocery stores with AI-powered parsing capabilities
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class ParsedItem:
    """Represents a parsed grocery item"""

    name: str
    brand: str = ""
    quantity: float = 1.0
    unit: str = "item"
    price: Optional[float] = None
    category: str = ""
    barcode: str = ""
    raw_text: str = ""
    line_number: int = 0
    confidence_score: float = 0.0


@dataclass
class ParsedReceipt:
    """Represents a parsed receipt"""

    store_name: str = ""
    store_address: str = ""
    purchase_date: Optional[date] = None
    transaction_id: str = ""
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    items: List[ParsedItem] = None
    confidence_score: float = 0.0
    parsing_errors: List[str] = None

    def __post_init__(self):
        if self.items is None:
            self.items = []
        if self.parsing_errors is None:
            self.parsing_errors = []


class EnhancedReceiptParser:
    """Enhanced receipt parser with store-specific logic"""

    def __init__(self):
        self.store_parsers = {
            "instacart": InstacartParser(),
            "amazon_fresh": AmazonFreshParser(),
            "walmart": WalmartParser(),
            "target": TargetParser(),
            "kroger": KrogerParser(),
            "safeway": SafewayParser(),
            "costco": CostcoParser(),
            "wholefoods": WholeFoodsParser(),
        }

        self.generic_parser = GenericParser()

    def parse_email_receipt(self, email_data: Dict) -> ParsedReceipt:
        """Parse receipt from email data"""
        sender = email_data.get("sender", "").lower()
        subject = email_data.get("subject", "").lower()
        body = email_data.get("body", "")

        # Detect store
        store_type = self._detect_store(sender, subject, body)

        # Use appropriate parser
        if store_type and store_type in self.store_parsers:
            parser = self.store_parsers[store_type]
            logger.info(f"Using {store_type} parser for receipt")
        else:
            parser = self.generic_parser
            logger.info("Using generic parser for receipt")

        # Parse receipt
        try:
            receipt = parser.parse(email_data)
            receipt.store_name = store_type or "Unknown Store"

            # Post-process and validate
            self._post_process_receipt(receipt)

            return receipt

        except Exception as e:
            logger.error(f"Error parsing receipt: {e}")
            return ParsedReceipt(
                store_name="Unknown Store",
                parsing_errors=[f"Parsing failed: {str(e)}"],
                confidence_score=0.0,
            )

    def _detect_store(self, sender: str, subject: str, body: str) -> Optional[str]:
        """Detect store from email metadata"""

        store_indicators = {
            "instacart": ["instacart.com", "instacart", "your instacart order"],
            "amazon_fresh": [
                "amazon.com",
                "amazonfresh",
                "amazon fresh",
                "whole foods",
            ],
            "walmart": ["walmart.com", "walmart", "walmart grocery"],
            "target": ["target.com", "target", "target.com"],
            "kroger": ["kroger.com", "kroger", "king soopers", "fred meyer"],
            "safeway": ["safeway.com", "safeway", "vons", "pavilions"],
            "costco": ["costco.com", "costco", "costco wholesale"],
            "wholefoods": ["wholefoods", "whole foods", "wholefoodsmarket"],
        }

        text_to_check = f"{sender} {subject} {body[:500]}".lower()

        for store, indicators in store_indicators.items():
            for indicator in indicators:
                if indicator in text_to_check:
                    return store

        return None

    def _post_process_receipt(self, receipt: ParsedReceipt):
        """Post-process parsed receipt for quality improvements"""

        # Remove duplicate items
        unique_items = []
        seen_items = set()

        for item in receipt.items:
            item_key = f"{item.name.lower()}_{item.quantity}_{item.price}"
            if item_key not in seen_items:
                unique_items.append(item)
                seen_items.add(item_key)

        receipt.items = unique_items

        # Infer categories for items
        for item in receipt.items:
            if not item.category:
                item.category = self._infer_category(item.name)

        # Calculate overall confidence
        if receipt.items:
            avg_confidence = sum(item.confidence_score for item in receipt.items) / len(
                receipt.items
            )
            structure_bonus = 0.1 if receipt.total else 0.0
            date_bonus = 0.1 if receipt.purchase_date else 0.0
            receipt.confidence_score = min(
                avg_confidence + structure_bonus + date_bonus, 1.0
            )
        else:
            receipt.confidence_score = 0.0

    def _infer_category(self, item_name: str) -> str:
        """Infer product category from item name"""
        name_lower = item_name.lower()

        categories = {
            "Produce": [
                "apple",
                "banana",
                "orange",
                "lettuce",
                "tomato",
                "carrot",
                "onion",
                "potato",
                "broccoli",
                "spinach",
                "avocado",
                "berry",
                "fruit",
                "vegetable",
                "organic",
                "fresh",
            ],
            "Dairy": [
                "milk",
                "cheese",
                "yogurt",
                "butter",
                "cream",
                "dairy",
                "eggs",
                "egg",
            ],
            "Meat & Seafood": [
                "chicken",
                "beef",
                "pork",
                "fish",
                "salmon",
                "tuna",
                "shrimp",
                "meat",
                "turkey",
                "ham",
                "bacon",
            ],
            "Pantry": [
                "bread",
                "pasta",
                "rice",
                "cereal",
                "beans",
                "sauce",
                "oil",
                "vinegar",
                "flour",
                "sugar",
                "salt",
                "spice",
            ],
            "Frozen": [
                "frozen",
                "ice cream",
                "pizza",
                "frozen fruit",
                "frozen vegetable",
            ],
            "Beverages": [
                "water",
                "juice",
                "soda",
                "coffee",
                "tea",
                "drink",
                "beverage",
                "wine",
                "beer",
            ],
            "Snacks": [
                "chips",
                "crackers",
                "nuts",
                "candy",
                "chocolate",
                "cookies",
                "snack",
                "granola",
            ],
            "Health & Beauty": [
                "shampoo",
                "soap",
                "toothpaste",
                "vitamin",
                "medicine",
                "lotion",
                "deodorant",
            ],
            "Household": [
                "detergent",
                "cleaner",
                "paper towel",
                "toilet paper",
                "dish soap",
                "laundry",
            ],
        }

        for category, keywords in categories.items():
            if any(keyword in name_lower for keyword in keywords):
                return category

        return "Other"


class BaseStoreParser:
    """Base class for store-specific parsers"""

    def __init__(self):
        self.store_name = "Unknown"
        self.currency_symbol = "$"

    def parse(self, email_data: Dict) -> ParsedReceipt:
        """Parse receipt - to be implemented by subclasses"""
        raise NotImplementedError

    def _extract_date(self, text: str, patterns: List[str]) -> Optional[date]:
        """Extract date using provided patterns"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                return self._parse_date_string(date_str)
        return None

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        date_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%m-%d-%Y",
            "%d-%m-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _extract_money(self, text: str) -> Optional[float]:
        """Extract money amount from text"""
        match = re.search(r"\$?([\d,]+\.?\d*)", text)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                pass
        return None

    def _clean_item_name(self, name: str) -> str:
        """Clean item name"""
        # Remove quantity prefixes
        name = re.sub(r"^\d+\.?\d*\s*x\s*", "", name, flags=re.IGNORECASE)
        # Remove price suffixes
        name = re.sub(r"\s*\$?[\d.,]+$", "", name)
        # Remove parenthetical info
        name = re.sub(r"\s*\(.*?\)$", "", name)
        # Clean whitespace
        name = re.sub(r"\s+", " ", name).strip()
        return name

    def _calculate_item_confidence(self, item: ParsedItem) -> float:
        """Calculate confidence score for an item"""
        score = 0.0

        # Name quality (50% of score)
        if item.name and len(item.name) > 2:
            score += 0.3
            if len(item.name) > 5:
                score += 0.1
            if not re.search(r"^\d+$", item.name):  # Not just numbers
                score += 0.1

        # Quantity (20% of score)
        if item.quantity and item.quantity > 0:
            score += 0.2

        # Price (20% of score)
        if item.price and item.price > 0:
            score += 0.2

        # Text structure (10% of score)
        if "$" in item.raw_text:
            score += 0.05
        if re.search(r"\d+\.?\d*\s*x\s*", item.raw_text):
            score += 0.05

        return min(score, 1.0)

    def _detect_unit(self, name: str) -> str:
        """Detect unit from item name"""
        name_lower = name.lower()

        unit_patterns = [
            (r"\b\d+\.?\d*\s*(oz|ounce|ounces)\b", "oz"),
            (r"\b\d+\.?\d*\s*(lb|lbs|pound|pounds)\b", "lb"),
            (r"\b\d+\.?\d*\s*(gal|gallon|gallons)\b", "gal"),
            (r"\b\d+\.?\d*\s*(qt|quart|quarts)\b", "qt"),
            (r"\b(pack|package|pkg)\b", "pack"),
            (r"\b(each|ea)\b", "each"),
            (r"\b(bag|bags)\b", "bag"),
            (r"\b(box|boxes)\b", "box"),
            (r"\b(bottle|bottles)\b", "bottle"),
        ]

        for pattern, unit in unit_patterns:
            if re.search(pattern, name_lower):
                return unit

        return "item"


class InstacartParser(BaseStoreParser):
    """Parser for Instacart receipts"""

    def __init__(self):
        super().__init__()
        self.store_name = "Instacart"

    def parse(self, email_data: Dict) -> ParsedReceipt:
        body = email_data.get("body", "")
        subject = email_data.get("subject", "")

        receipt = ParsedReceipt(store_name=self.store_name)

        # Extract basic info
        receipt.purchase_date = self._extract_date(
            body,
            [
                r"delivered on (.+?)(?:\n|$)",
                r"order placed (.+?)(?:\n|$)",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ],
        )

        receipt.transaction_id = self._extract_transaction_id(body)

        # Extract totals
        receipt.subtotal = self._extract_subtotal(body)
        receipt.tax = self._extract_tax(body)
        receipt.total = self._extract_total(body)

        # Parse items
        receipt.items = self._parse_instacart_items(body)

        return receipt

    def _extract_transaction_id(self, text: str) -> str:
        """Extract Instacart order ID"""
        patterns = [
            r"order #([A-Z0-9]+)",
            r"order number:?\s*([A-Z0-9]+)",
            r"confirmation:?\s*([A-Z0-9]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    def _extract_subtotal(self, text: str) -> Optional[float]:
        """Extract subtotal"""
        match = re.search(r"subtotal:?\s*\$?([\d,]+\.?\d*)", text, re.IGNORECASE)
        return self._extract_money(match.group(0)) if match else None

    def _extract_tax(self, text: str) -> Optional[float]:
        """Extract tax amount"""
        match = re.search(r"tax:?\s*\$?([\d,]+\.?\d*)", text, re.IGNORECASE)
        return self._extract_money(match.group(0)) if match else None

    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total amount"""
        patterns = [
            r"total:?\s*\$?([\d,]+\.?\d*)",
            r"amount charged:?\s*\$?([\d,]+\.?\d*)",
            r"grand total:?\s*\$?([\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._extract_money(match.group(0))
        return None

    def _parse_instacart_items(self, text: str) -> List[ParsedItem]:
        """Parse Instacart items from receipt text"""
        items = []
        lines = text.split("\n")

        # Look for item section
        in_items_section = False

        for i, line in enumerate(lines):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check for start of items section
            if re.search(
                r"(your order|items ordered|grocery items)", line, re.IGNORECASE
            ):
                in_items_section = True
                continue

            # Check for end of items section
            if re.search(r"(subtotal|total|delivery|tip|fees)", line, re.IGNORECASE):
                in_items_section = False
                continue

            if in_items_section:
                item = self._parse_instacart_item_line(line, i)
                if item:
                    items.append(item)

        return items

    def _parse_instacart_item_line(
        self, line: str, line_number: int
    ) -> Optional[ParsedItem]:
        """Parse a single Instacart item line"""

        # Common Instacart patterns
        patterns = [
            r"(\d+\.?\d*)\s*x\s*(.+?)\s*\$?([\d,]+\.?\d*)$",  # "2 x Bananas $3.99"
            r"(.+?)\s*\$?([\d,]+\.?\d*)$",  # "Bananas $3.99"
            r"(.+?)\s*qty:?\s*(\d+\.?\d*)\s*\$?([\d,]+\.?\d*)$",  # "Bananas qty: 2 $3.99"
        ]

        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                groups = match.groups()

                if len(groups) == 3:
                    if re.match(r"^\d+\.?\d*$", groups[0]):
                        # quantity, name, price
                        quantity, name, price = groups
                    else:
                        # name, quantity, price
                        name, quantity, price = groups
                elif len(groups) == 2:
                    # name, price
                    name, price = groups
                    quantity = "1"
                else:
                    continue

                # Create item
                item = ParsedItem(
                    name=self._clean_item_name(name),
                    quantity=(
                        float(quantity)
                        if quantity and quantity.replace(".", "").isdigit()
                        else 1.0
                    ),
                    price=self._extract_money(price) if price else None,
                    unit=self._detect_unit(name),
                    raw_text=line,
                    line_number=line_number,
                )

                item.confidence_score = self._calculate_item_confidence(item)
                return item

        return None


class AmazonFreshParser(BaseStoreParser):
    """Parser for Amazon Fresh receipts"""

    def __init__(self):
        super().__init__()
        self.store_name = "Amazon Fresh"

    def parse(self, email_data: Dict) -> ParsedReceipt:
        body = email_data.get("body", "")

        receipt = ParsedReceipt(store_name=self.store_name)

        # Extract date
        receipt.purchase_date = self._extract_date(
            body,
            [
                r"delivered (.+?)(?:\n|$)",
                r"order date:? (.+?)(?:\n|$)",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ],
        )

        # Extract totals
        receipt.total = self._extract_total(body)

        # Parse items
        receipt.items = self._parse_amazon_items(body)

        return receipt

    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total from Amazon receipt"""
        patterns = [
            r"order total:?\s*\$?([\d,]+\.?\d*)",
            r"total:?\s*\$?([\d,]+\.?\d*)",
            r"amount:?\s*\$?([\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._extract_money(match.group(0))
        return None

    def _parse_amazon_items(self, text: str) -> List[ParsedItem]:
        """Parse Amazon Fresh items"""
        items = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Skip non-item lines
            if self._should_skip_amazon_line(line):
                continue

            item = self._parse_amazon_item_line(line, i)
            if item:
                items.append(item)

        return items

    def _should_skip_amazon_line(self, line: str) -> bool:
        """Check if line should be skipped for Amazon"""
        skip_patterns = [
            r"order total",
            r"shipping",
            r"tax",
            r"prime",
            r"discount",
            r"promotion",
            r"credit",
            r"gift card",
            r"your order",
            r"delivered",
            r"tracking",
            r"return",
        ]

        line_lower = line.lower()
        for pattern in skip_patterns:
            if re.search(pattern, line_lower):
                return True
        return False

    def _parse_amazon_item_line(
        self, line: str, line_number: int
    ) -> Optional[ParsedItem]:
        """Parse Amazon Fresh item line"""
        # Amazon patterns
        patterns = [
            r"(.+?)\s*\$?([\d,]+\.?\d*)$",  # "Item Name $4.99"
            r"(\d+\.?\d*)\s*x\s*(.+?)\s*\$?([\d,]+\.?\d*)$",  # "2 x Item Name $4.99"
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()

                if len(groups) == 3:
                    quantity, name, price = groups
                elif len(groups) == 2:
                    name, price = groups
                    quantity = "1"
                else:
                    continue

                item = ParsedItem(
                    name=self._clean_item_name(name),
                    quantity=(
                        float(quantity)
                        if quantity and quantity.replace(".", "").isdigit()
                        else 1.0
                    ),
                    price=self._extract_money(price) if price else None,
                    unit=self._detect_unit(name),
                    raw_text=line,
                    line_number=line_number,
                )

                item.confidence_score = self._calculate_item_confidence(item)
                return item

        return None


class WalmartParser(BaseStoreParser):
    """Parser for Walmart receipts"""

    def __init__(self):
        super().__init__()
        self.store_name = "Walmart"

    def parse(self, email_data: Dict) -> ParsedReceipt:
        body = email_data.get("body", "")

        receipt = ParsedReceipt(store_name=self.store_name)

        # Extract date
        receipt.purchase_date = self._extract_date(
            body,
            [
                r"pickup date:? (.+?)(?:\n|$)",
                r"order date:? (.+?)(?:\n|$)",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ],
        )

        # Extract totals
        receipt.total = self._extract_total(body)

        # Parse items
        receipt.items = self._parse_walmart_items(body)

        return receipt

    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total from Walmart receipt"""
        patterns = [
            r"total:?\s*\$?([\d,]+\.?\d*)",
            r"amount:?\s*\$?([\d,]+\.?\d*)",
            r"order total:?\s*\$?([\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._extract_money(match.group(0))
        return None

    def _parse_walmart_items(self, text: str) -> List[ParsedItem]:
        """Parse Walmart items"""
        items = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            if self._should_skip_walmart_line(line):
                continue

            item = self._parse_walmart_item_line(line, i)
            if item:
                items.append(item)

        return items

    def _should_skip_walmart_line(self, line: str) -> bool:
        """Check if line should be skipped for Walmart"""
        skip_patterns = [
            r"subtotal",
            r"tax",
            r"total",
            r"savings",
            r"pickup",
            r"discount",
            r"coupon",
            r"walmart",
            r"order",
            r"confirmation",
        ]

        line_lower = line.lower()
        for pattern in skip_patterns:
            if re.search(pattern, line_lower):
                return True
        return False

    def _parse_walmart_item_line(
        self, line: str, line_number: int
    ) -> Optional[ParsedItem]:
        """Parse Walmart item line"""
        patterns = [
            r"(.+?)\s*\$?([\d,]+\.?\d*)$",
            r"(\d+\.?\d*)\s+(.+?)\s*\$?([\d,]+\.?\d*)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()

                if len(groups) == 3:
                    quantity, name, price = groups
                elif len(groups) == 2:
                    name, price = groups
                    quantity = "1"
                else:
                    continue

                item = ParsedItem(
                    name=self._clean_item_name(name),
                    quantity=(
                        float(quantity)
                        if quantity and quantity.replace(".", "").isdigit()
                        else 1.0
                    ),
                    price=self._extract_money(price) if price else None,
                    unit=self._detect_unit(name),
                    raw_text=line,
                    line_number=line_number,
                )

                item.confidence_score = self._calculate_item_confidence(item)
                return item

        return None


# Additional store parsers
class TargetParser(BaseStoreParser):
    """Parser for Target receipts"""

    def __init__(self):
        super().__init__()
        self.store_name = "Target"

    def parse(self, email_data: Dict) -> ParsedReceipt:
        body = email_data.get("body", "")

        receipt = ParsedReceipt(store_name=self.store_name)

        # Extract date
        receipt.purchase_date = self._extract_date(
            body,
            [
                r"order date:? (.+?)(?:\n|$)",
                r"pickup date:? (.+?)(?:\n|$)",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ],
        )

        # Extract totals
        receipt.total = self._extract_total(body)
        receipt.subtotal = self._extract_subtotal(body)

        # Parse items
        receipt.items = self._parse_target_items(body)

        return receipt

    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total from Target receipt"""
        patterns = [
            r"total:?\s*\$?([\\d,]+\.?\d*)",
            r"amount:?\s*\$?([\\d,]+\.?\d*)",
            r"order total:?\s*\$?([\\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._extract_money(match.group(0))
        return None

    def _extract_subtotal(self, text: str) -> Optional[float]:
        """Extract subtotal"""
        match = re.search(r"subtotal:?\s*\$?([\\d,]+\.?\d*)", text, re.IGNORECASE)
        return self._extract_money(match.group(0)) if match else None

    def _parse_target_items(self, text: str) -> List[ParsedItem]:
        """Parse Target items"""
        items = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or self._should_skip_target_line(line):
                continue

            item = self._parse_target_item_line(line, i)
            if item:
                items.append(item)

        return items

    def _should_skip_target_line(self, line: str) -> bool:
        """Check if line should be skipped for Target"""
        skip_patterns = [
            r"subtotal",
            r"tax",
            r"total",
            r"redcard",
            r"circle",
            r"discount",
            r"promotion",
            r"target",
            r"order",
            r"pickup",
        ]

        line_lower = line.lower()
        for pattern in skip_patterns:
            if re.search(pattern, line_lower):
                return True
        return False

    def _parse_target_item_line(
        self, line: str, line_number: int
    ) -> Optional[ParsedItem]:
        """Parse Target item line"""
        patterns = [
            r"(.+?)\s*\$?([\\d,]+\.?\d*)$",
            r"(\d+\.?\d*)\s+(.+?)\s*\$?([\\d,]+\.?\d*)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()

                if len(groups) == 3:
                    quantity, name, price = groups
                elif len(groups) == 2:
                    name, price = groups
                    quantity = "1"
                else:
                    continue

                item = ParsedItem(
                    name=self._clean_item_name(name),
                    quantity=(
                        float(quantity)
                        if quantity and quantity.replace(".", "").isdigit()
                        else 1.0
                    ),
                    price=self._extract_money(price) if price else None,
                    unit=self._detect_unit(name),
                    raw_text=line,
                    line_number=line_number,
                )

                item.confidence_score = self._calculate_item_confidence(item)
                return item

        return None


class KrogerParser(BaseStoreParser):
    """Parser for Kroger family stores (Kroger, King Soopers, Fred Meyer)"""

    def __init__(self):
        super().__init__()
        self.store_name = "Kroger"

    def parse(self, email_data: Dict) -> ParsedReceipt:
        body = email_data.get("body", "")

        receipt = ParsedReceipt(store_name=self.store_name)

        # Extract date
        receipt.purchase_date = self._extract_date(
            body,
            [
                r"order date:? (.+?)(?:\n|$)",
                r"pickup date:? (.+?)(?:\n|$)",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ],
        )

        # Extract totals
        receipt.total = self._extract_total(body)

        # Parse items
        receipt.items = self._parse_kroger_items(body)

        return receipt

    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total from Kroger receipt"""
        patterns = [
            r"total:?\s*\$?([\\d,]+\.?\d*)",
            r"amount due:?\s*\$?([\\d,]+\.?\d*)",
            r"order total:?\s*\$?([\\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._extract_money(match.group(0))
        return None

    def _parse_kroger_items(self, text: str) -> List[ParsedItem]:
        """Parse Kroger items"""
        items = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or self._should_skip_kroger_line(line):
                continue

            item = self._parse_kroger_item_line(line, i)
            if item:
                items.append(item)

        return items

    def _should_skip_kroger_line(self, line: str) -> bool:
        """Check if line should be skipped for Kroger"""
        skip_patterns = [
            r"subtotal",
            r"tax",
            r"total",
            r"savings",
            r"fuel points",
            r"discount",
            r"coupon",
            r"kroger",
            r"king soopers",
            r"fred meyer",
        ]

        line_lower = line.lower()
        for pattern in skip_patterns:
            if re.search(pattern, line_lower):
                return True
        return False

    def _parse_kroger_item_line(
        self, line: str, line_number: int
    ) -> Optional[ParsedItem]:
        """Parse Kroger item line"""
        patterns = [
            r"(.+?)\s*\$?([\\d,]+\.?\d*)$",
            r"(\d+\.?\d*)\s+(.+?)\s*\$?([\\d,]+\.?\d*)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()

                if len(groups) == 3:
                    quantity, name, price = groups
                elif len(groups) == 2:
                    name, price = groups
                    quantity = "1"
                else:
                    continue

                item = ParsedItem(
                    name=self._clean_item_name(name),
                    quantity=(
                        float(quantity)
                        if quantity and quantity.replace(".", "").isdigit()
                        else 1.0
                    ),
                    price=self._extract_money(price) if price else None,
                    unit=self._detect_unit(name),
                    raw_text=line,
                    line_number=line_number,
                )

                item.confidence_score = self._calculate_item_confidence(item)
                return item

        return None


class SafewayParser(BaseStoreParser):
    """Parser for Safeway family stores (Safeway, Vons, Pavilions)"""

    def __init__(self):
        super().__init__()
        self.store_name = "Safeway"

    def parse(self, email_data: Dict) -> ParsedReceipt:
        body = email_data.get("body", "")

        receipt = ParsedReceipt(store_name=self.store_name)

        # Extract date
        receipt.purchase_date = self._extract_date(
            body,
            [
                r"order date:? (.+?)(?:\n|$)",
                r"delivery date:? (.+?)(?:\n|$)",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ],
        )

        # Extract totals
        receipt.total = self._extract_total(body)

        # Parse items
        receipt.items = self._parse_safeway_items(body)

        return receipt

    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total from Safeway receipt"""
        patterns = [
            r"total:?\s*\$?([\\d,]+\.?\d*)",
            r"order total:?\s*\$?([\\d,]+\.?\d*)",
            r"amount charged:?\s*\$?([\\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._extract_money(match.group(0))
        return None

    def _parse_safeway_items(self, text: str) -> List[ParsedItem]:
        """Parse Safeway items"""
        items = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or self._should_skip_safeway_line(line):
                continue

            item = self._parse_safeway_item_line(line, i)
            if item:
                items.append(item)

        return items

    def _should_skip_safeway_line(self, line: str) -> bool:
        """Check if line should be skipped for Safeway"""
        skip_patterns = [
            r"subtotal",
            r"tax",
            r"total",
            r"savings",
            r"club card",
            r"discount",
            r"coupon",
            r"safeway",
            r"vons",
            r"pavilions",
        ]

        line_lower = line.lower()
        for pattern in skip_patterns:
            if re.search(pattern, line_lower):
                return True
        return False

    def _parse_safeway_item_line(
        self, line: str, line_number: int
    ) -> Optional[ParsedItem]:
        """Parse Safeway item line"""
        patterns = [
            r"(.+?)\s*\$?([\\d,]+\.?\d*)$",
            r"(\d+\.?\d*)\s+(.+?)\s*\$?([\\d,]+\.?\d*)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()

                if len(groups) == 3:
                    quantity, name, price = groups
                elif len(groups) == 2:
                    name, price = groups
                    quantity = "1"
                else:
                    continue

                item = ParsedItem(
                    name=self._clean_item_name(name),
                    quantity=(
                        float(quantity)
                        if quantity and quantity.replace(".", "").isdigit()
                        else 1.0
                    ),
                    price=self._extract_money(price) if price else None,
                    unit=self._detect_unit(name),
                    raw_text=line,
                    line_number=line_number,
                )

                item.confidence_score = self._calculate_item_confidence(item)
                return item

        return None


class CostcoParser(BaseStoreParser):
    """Parser for Costco receipts"""

    def __init__(self):
        super().__init__()
        self.store_name = "Costco"

    def parse(self, email_data: Dict) -> ParsedReceipt:
        body = email_data.get("body", "")

        receipt = ParsedReceipt(store_name=self.store_name)

        # Extract date
        receipt.purchase_date = self._extract_date(
            body,
            [
                r"order date:? (.+?)(?:\n|$)",
                r"transaction date:? (.+?)(?:\n|$)",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ],
        )

        # Extract totals
        receipt.total = self._extract_total(body)

        # Parse items
        receipt.items = self._parse_costco_items(body)

        return receipt

    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total from Costco receipt"""
        patterns = [
            r"total:?\s*\$?([\\d,]+\.?\d*)",
            r"order total:?\s*\$?([\\d,]+\.?\d*)",
            r"merchandise total:?\s*\$?([\\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._extract_money(match.group(0))
        return None

    def _parse_costco_items(self, text: str) -> List[ParsedItem]:
        """Parse Costco items"""
        items = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or self._should_skip_costco_line(line):
                continue

            item = self._parse_costco_item_line(line, i)
            if item:
                items.append(item)

        return items

    def _should_skip_costco_line(self, line: str) -> bool:
        """Check if line should be skipped for Costco"""
        skip_patterns = [
            r"subtotal",
            r"tax",
            r"total",
            r"membership",
            r"executive",
            r"discount",
            r"coupon",
            r"costco",
            r"warehouse",
        ]

        line_lower = line.lower()
        for pattern in skip_patterns:
            if re.search(pattern, line_lower):
                return True
        return False

    def _parse_costco_item_line(
        self, line: str, line_number: int
    ) -> Optional[ParsedItem]:
        """Parse Costco item line - often has item numbers"""
        patterns = [
            r"(\d+)\s+(.+?)\s*\$?([\\d,]+\.?\d*)$",  # "123456 Item Name $19.99"
            r"(.+?)\s*\$?([\\d,]+\.?\d*)$",  # "Item Name $19.99"
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()

                if len(groups) == 3:
                    # Skip item number, use name and price
                    _, name, price = groups
                    quantity = "1"
                elif len(groups) == 2:
                    name, price = groups
                    quantity = "1"
                else:
                    continue

                item = ParsedItem(
                    name=self._clean_item_name(name),
                    quantity=(
                        float(quantity)
                        if quantity and quantity.replace(".", "").isdigit()
                        else 1.0
                    ),
                    price=self._extract_money(price) if price else None,
                    unit=self._detect_unit(name),
                    raw_text=line,
                    line_number=line_number,
                )

                item.confidence_score = self._calculate_item_confidence(item)
                return item

        return None


class WholeFoodsParser(BaseStoreParser):
    """Parser for Whole Foods receipts"""

    def __init__(self):
        super().__init__()
        self.store_name = "Whole Foods"

    def parse(self, email_data: Dict) -> ParsedReceipt:
        body = email_data.get("body", "")

        receipt = ParsedReceipt(store_name=self.store_name)

        # Extract date
        receipt.purchase_date = self._extract_date(
            body,
            [
                r"order date:? (.+?)(?:\n|$)",
                r"delivery date:? (.+?)(?:\n|$)",
                r"(\d{1,2}/\d{1,2}/\d{4})",
            ],
        )

        # Extract totals
        receipt.total = self._extract_total(body)

        # Parse items
        receipt.items = self._parse_wholefoods_items(body)

        return receipt

    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total from Whole Foods receipt"""
        patterns = [
            r"total:?\s*\$?([\\d,]+\.?\d*)",
            r"order total:?\s*\$?([\\d,]+\.?\d*)",
            r"amount charged:?\s*\$?([\\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._extract_money(match.group(0))
        return None

    def _parse_wholefoods_items(self, text: str) -> List[ParsedItem]:
        """Parse Whole Foods items"""
        items = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or self._should_skip_wholefoods_line(line):
                continue

            item = self._parse_wholefoods_item_line(line, i)
            if item:
                items.append(item)

        return items

    def _should_skip_wholefoods_line(self, line: str) -> bool:
        """Check if line should be skipped for Whole Foods"""
        skip_patterns = [
            r"subtotal",
            r"tax",
            r"total",
            r"prime",
            r"discount",
            r"promotion",
            r"whole foods",
            r"amazon",
            r"delivery",
        ]

        line_lower = line.lower()
        for pattern in skip_patterns:
            if re.search(pattern, line_lower):
                return True
        return False

    def _parse_wholefoods_item_line(
        self, line: str, line_number: int
    ) -> Optional[ParsedItem]:
        """Parse Whole Foods item line"""
        patterns = [
            r"(.+?)\s*\$?([\\d,]+\.?\d*)$",
            r"(\d+\.?\d*)\s+(.+?)\s*\$?([\\d,]+\.?\d*)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()

                if len(groups) == 3:
                    quantity, name, price = groups
                elif len(groups) == 2:
                    name, price = groups
                    quantity = "1"
                else:
                    continue

                item = ParsedItem(
                    name=self._clean_item_name(name),
                    quantity=(
                        float(quantity)
                        if quantity and quantity.replace(".", "").isdigit()
                        else 1.0
                    ),
                    price=self._extract_money(price) if price else None,
                    unit=self._detect_unit(name),
                    raw_text=line,
                    line_number=line_number,
                )

                item.confidence_score = self._calculate_item_confidence(item)
                return item

        return None


class GenericParser(BaseStoreParser):
    """Generic parser for unknown stores"""

    def __init__(self):
        super().__init__()
        self.store_name = "Generic Store"

    def parse(self, email_data: Dict) -> ParsedReceipt:
        """Generic parsing logic"""
        body = email_data.get("body", "")

        receipt = ParsedReceipt(store_name="Unknown Store")

        # Try to extract basic info
        receipt.purchase_date = self._extract_date(
            body,
            [
                r"(\d{1,2}/\d{1,2}/\d{4})",
                r"(\d{4}-\d{2}-\d{2})",
                r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}",
            ],
        )

        receipt.total = self._extract_total_generic(body)

        # Parse items generically
        receipt.items = self._parse_generic_items(body)

        return receipt

    def _extract_total_generic(self, text: str) -> Optional[float]:
        """Generic total extraction"""
        patterns = [
            r"total:?\s*\$?([\d,]+\.?\d*)",
            r"amount:?\s*\$?([\d,]+\.?\d*)",
            r"grand total:?\s*\$?([\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._extract_money(match.group(0))
        return None

    def _parse_generic_items(self, text: str) -> List[ParsedItem]:
        """Generic item parsing"""
        items = []
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Skip obvious non-item lines
            if self._should_skip_generic_line(line):
                continue

            item = self._parse_generic_item_line(line, i)
            if item:
                items.append(item)

        return items

    def _should_skip_generic_line(self, line: str) -> bool:
        """Skip non-item lines"""
        skip_patterns = [
            r"^\s*[-=_]{3,}",
            r"thank you",
            r"receipt",
            r"order",
            r"customer",
            r"cashier",
            r"store",
            r"address",
            r"phone",
            r"subtotal",
            r"tax",
            r"total",
            r"discount",
            r"promotion",
        ]

        line_lower = line.lower()
        for pattern in skip_patterns:
            if re.search(pattern, line_lower):
                return True
        return False

    def _parse_generic_item_line(
        self, line: str, line_number: int
    ) -> Optional[ParsedItem]:
        """Generic item line parsing"""
        # Very basic pattern matching
        patterns = [
            r"(.+?)\s*\$?([\d,]+\.?\d*)$",  # "Item Name $4.99"
            r"(\d+\.?\d*)\s*x\s*(.+?)\s*\$?([\d,]+\.?\d*)$",  # "2 x Item $4.99"
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                groups = match.groups()

                if len(groups) == 3:
                    quantity, name, price = groups
                elif len(groups) == 2:
                    name, price = groups
                    quantity = "1"
                else:
                    continue

                # Basic validation
                if len(name.strip()) < 2:
                    continue

                item = ParsedItem(
                    name=self._clean_item_name(name),
                    quantity=(
                        float(quantity)
                        if quantity and quantity.replace(".", "").isdigit()
                        else 1.0
                    ),
                    price=self._extract_money(price) if price else None,
                    unit="item",
                    raw_text=line,
                    line_number=line_number,
                )

                item.confidence_score = (
                    self._calculate_item_confidence(item) * 0.7
                )  # Lower confidence for generic
                return item

        return None
