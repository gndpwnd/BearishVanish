"""
Ticker Validation Module
Validates and cleans stock ticker symbols to prevent database pollution
"""

import re

class TickerValidator:
    """Validates stock ticker symbols"""
    
    # Valid ticker patterns
    MIN_LENGTH = 1
    MAX_LENGTH = 6  # Most US tickers are 1-5 chars, some ADRs are 6
    
    # Common invalid patterns
    INVALID_PATTERNS = [
        r'^-+$',           # Just dashes
        r'^\s*$',          # Just whitespace
        r'^CASH',          # Cash entries
        r'^USD',           # Currency entries
        r'^Total',         # Summary rows
        r'copyright',      # Legal text (case insensitive)
        r'BlackRock',      # Legal text
        r'iShares',        # Legal text
        r'Holdings',       # Header text
        r'The content',    # Legal disclaimers
    ]
    
    @staticmethod
    def is_valid(ticker):
        """
        Check if a ticker symbol is valid
        
        Args:
            ticker: Ticker symbol string
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not ticker or not isinstance(ticker, str):
            return False
        
        ticker = ticker.strip()
        
        # Check length
        if len(ticker) < TickerValidator.MIN_LENGTH:
            return False
        if len(ticker) > TickerValidator.MAX_LENGTH:
            return False
        
        # Check for invalid patterns
        for pattern in TickerValidator.INVALID_PATTERNS:
            if re.search(pattern, ticker, re.IGNORECASE):
                return False
        
        # Must contain at least one letter
        if not re.search(r'[A-Za-z]', ticker):
            return False
        
        # Should only contain letters, dots, and dashes
        if not re.match(r'^[A-Za-z0-9.\-]+$', ticker):
            return False
        
        return True
    
    @staticmethod
    def clean_ticker(ticker):
        """
        Clean and normalize a ticker symbol
        
        Args:
            ticker: Raw ticker string
            
        Returns:
            str: Cleaned ticker or None if invalid
        """
        if not ticker:
            return None
        
        # Strip whitespace and convert to uppercase
        ticker = str(ticker).strip().upper()
        
        # Validate
        if not TickerValidator.is_valid(ticker):
            return None
        
        return ticker
    
    @staticmethod
    def clean_ticker_list(tickers):
        """
        Clean a list of tickers, removing invalid ones
        
        Args:
            tickers: List of ticker strings
            
        Returns:
            tuple: (valid_tickers, invalid_tickers, stats)
        """
        valid = []
        invalid = []
        
        stats = {
            'total': len(tickers),
            'valid': 0,
            'invalid': 0,
            'duplicates': 0,
            'too_short': 0,
            'too_long': 0,
            'invalid_chars': 0,
            'legal_text': 0
        }
        
        seen = set()
        
        for ticker in tickers:
            cleaned = TickerValidator.clean_ticker(ticker)
            
            if cleaned:
                # Check for duplicates
                if cleaned in seen:
                    invalid.append((ticker, 'duplicate'))
                    stats['duplicates'] += 1
                else:
                    valid.append(cleaned)
                    seen.add(cleaned)
                    stats['valid'] += 1
            else:
                # Categorize why it's invalid
                if not ticker or len(str(ticker).strip()) == 0:
                    invalid.append((ticker, 'empty'))
                elif len(str(ticker).strip()) < TickerValidator.MIN_LENGTH:
                    invalid.append((ticker, 'too_short'))
                    stats['too_short'] += 1
                elif len(str(ticker).strip()) > TickerValidator.MAX_LENGTH:
                    invalid.append((ticker, 'too_long'))
                    stats['too_long'] += 1
                    stats['legal_text'] += 1  # Long entries are usually legal text
                elif re.search(r'[^A-Za-z0-9.\-]', str(ticker).strip()):
                    invalid.append((ticker, 'invalid_chars'))
                    stats['invalid_chars'] += 1
                else:
                    invalid.append((ticker, 'invalid_pattern'))
                
                stats['invalid'] += 1
        
        return valid, invalid, stats
    
    @staticmethod
    def print_validation_report(tickers):
        """
        Print a detailed validation report
        
        Args:
            tickers: List of tickers to validate
        """
        valid, invalid, stats = TickerValidator.clean_ticker_list(tickers)
        
        print(f"\n{'='*70}")
        print(f"TICKER VALIDATION REPORT")
        print(f"{'='*70}")
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total entries:     {stats['total']}")
        print(f"  Valid tickers:     {stats['valid']} ({stats['valid']/stats['total']*100:.1f}%)")
        print(f"  Invalid entries:   {stats['invalid']} ({stats['invalid']/stats['total']*100:.1f}%)")
        
        if stats['invalid'] > 0:
            print(f"\n❌ INVALID BREAKDOWN:")
            if stats['too_short'] > 0:
                print(f"  Too short:         {stats['too_short']}")
            if stats['too_long'] > 0:
                print(f"  Too long:          {stats['too_long']} (likely legal text)")
            if stats['duplicates'] > 0:
                print(f"  Duplicates:        {stats['duplicates']}")
            if stats['invalid_chars'] > 0:
                print(f"  Invalid chars:     {stats['invalid_chars']}")
        
        if invalid and len(invalid) <= 20:
            print(f"\n🔍 INVALID ENTRIES:")
            for ticker, reason in invalid[:20]:
                # Truncate long entries
                display = str(ticker)[:50] + "..." if len(str(ticker)) > 50 else str(ticker)
                print(f"  • '{display}' ({reason})")
        elif invalid:
            print(f"\n🔍 SAMPLE INVALID ENTRIES (first 10):")
            for ticker, reason in invalid[:10]:
                display = str(ticker)[:50] + "..." if len(str(ticker)) > 50 else str(ticker)
                print(f"  • '{display}' ({reason})")
            print(f"  ... and {len(invalid) - 10} more")
        
        print(f"\n✅ VALID TICKERS ({stats['valid']} total):")
        print(f"  Sample: {', '.join(valid[:10])}")
        if stats['valid'] > 10:
            print(f"  ... and {stats['valid'] - 10} more")
        
        print(f"\n{'='*70}\n")
        
        return valid, invalid, stats


def validate_ticker_simple(ticker):
    """
    Quick validation function for inline use
    
    Args:
        ticker: Ticker symbol
        
    Returns:
        bool: True if valid
    """
    return TickerValidator.is_valid(ticker)


def clean_tickers(tickers):
    """
    Quick clean function for inline use
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        list: Cleaned, valid tickers
    """
    valid, _, _ = TickerValidator.clean_ticker_list(tickers)
    return valid