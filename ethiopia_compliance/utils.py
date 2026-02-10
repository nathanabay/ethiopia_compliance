import frappe
from frappe.utils import add_days, getdate, formatdate
import datetime

# --- ETHIOPIAN CALENDAR LOGIC ---

@frappe.whitelist()
def get_ec_date(date):
    """API Endpoint: Convert Gregorian to Ethiopian"""
    if not date: return ""
    
    try:
        from ethiopian_date import EthiopianDateConverter
        
        # 1. Parse Input Date
        d = getdate(date)
        
        # 2. Convert
        ec = EthiopianDateConverter.to_ethiopian(d.year, d.month, d.day)
        
        # 3. Handle Result (Fixing the error here)
        # Check if it's a tuple/list or an object
        if isinstance(ec, (tuple, list)):
            # Format: (Year, Month, Day)
            return f"{ec[2]:02d}-{ec[1]:02d}-{ec[0]}"
        elif hasattr(ec, 'day'):
            # It is a Date Object
            return f"{ec.day:02d}-{ec.month:02d}-{ec.year}"
        else:
            return str(ec)

    except ImportError:
        return "Err: Lib Missing"
    except Exception as e:
        frappe.log_error(f"EC Date Error: {str(e)}")
        return ""

@frappe.whitelist()
def get_gc_date(ethiopian_date):
    """API Endpoint: Convert Ethiopian DD-MM-YYYY to Gregorian"""
    if not ethiopian_date: return ""
    
    try:
        from ethiopian_date import EthiopianDateConverter
        
        # Expecting DD-MM-YYYY
        parts = ethiopian_date.split('-')
        if len(parts) != 3: return ""
        
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        
        gc = EthiopianDateConverter.to_gregorian(y, m, d)
        
        # Handle Result
        if isinstance(gc, (tuple, list)):
            return f"{gc[0]}-{gc[1]:02d}-{gc[2]:02d}"
        elif hasattr(gc, 'day'):
            return f"{gc.year}-{gc.month:02d}-{gc.day:02d}"
        else:
            return str(gc)

    except Exception as e:
        frappe.log_error(f"GC Date Error: {str(e)}")
        return ""
