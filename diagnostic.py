#!/usr/bin/env python3
"""
System Diagnostic Tool
Verifies that all components are properly configured before live trading.
"""
import sys
import os

def check_dependencies():
    """Check if required packages are installed"""
    print("🔍 Checking dependencies...")
    
    required = {
        'numpy': 'numpy',
        'pandas': 'pandas',
        'xgboost': 'xgboost',
        'sklearn': 'scikit-learn',
    }
    
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing.append(package)
    
    # Check for Groww API
    try:
        import growwapi
        print(f"  ✅ growwapi")
    except ImportError:
        print(f"  ⚠️  growwapi - MISSING (needed for live trading)")
        print("     Install: pip install growwapi")
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def check_configuration():
    """Check config.py settings"""
    print("\n🔍 Checking configuration...")
    
    try:
        import config
        
        # Check API credentials
        if config.GROWW_API_TOKEN == "your_groww_token_here":
            print("  ⚠️  Groww API token not configured")
            print("     Edit config.py or create .env file")
        else:
            print("  ✅ Groww API token configured")
        
        # Check trading mode
        if config.TRADING_MODE not in ["paper", "live"]:
            print(f"  ❌ Invalid TRADING_MODE: {config.TRADING_MODE}")
            return False
        else:
            print(f"  ✅ Trading mode: {config.TRADING_MODE}")
        
        # Check symbols
        if not config.SYMBOLS:
            print("  ❌ No symbols configured")
            return False
        else:
            print(f"  ✅ Symbols: {', '.join(config.SYMBOLS)}")
        
        # Check risk limits
        if config.MAX_POSITION_SIZE <= 0:
            print("  ❌ Invalid MAX_POSITION_SIZE")
            return False
        
        print(f"  ✅ Max position size: ₹{config.MAX_POSITION_SIZE:,}")
        print(f"  ✅ Daily loss limit: ₹{config.MAX_LOSS_PER_DAY:,}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False

def check_database():
    """Check database connectivity"""
    print("\n🔍 Checking database...")
    
    try:
        from database import TradingDatabase
        
        db = TradingDatabase()
        db.log_event("DIAGNOSTIC", "Database check", "INFO")
        print("  ✅ Database initialized successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def check_model():
    """Check if XGBoost model exists"""
    print("\n🔍 Checking ML model...")
    
    import config
    
    if os.path.exists(config.XGBOOST_MODEL_PATH):
        print(f"  ✅ Model found at {config.XGBOOST_MODEL_PATH}")
        return True
    else:
        print(f"  ⚠️  Model not found at {config.XGBOOST_MODEL_PATH}")
        print("     Strategy will use placeholder logic")
        print("     Train your model and save to this path")
        return False

def check_file_structure():
    """Verify all required files exist"""
    print("\n🔍 Checking file structure...")
    
    required_files = [
        'config.py',
        'interfaces.py',
        'database.py',
        'main.py',
        'brokers/groww_adapter.py',
        'brokers/paper_adapter.py',
        'strategies/strategy_engine.py',
        'utils/risk_manager.py',
    ]
    
    all_exist = True
    for filepath in required_files:
        if os.path.exists(filepath):
            print(f"  ✅ {filepath}")
        else:
            print(f"  ❌ {filepath} - MISSING")
            all_exist = False
    
    return all_exist

def main():
    """Run all diagnostic checks"""
    print("="*60)
    print("🏥 TRADING SYSTEM DIAGNOSTIC")
    print("="*60)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("File Structure", check_file_structure),
        ("Configuration", check_configuration),
        ("Database", check_database),
        ("ML Model", check_model),
    ]
    
    results = {}
    for name, check_func in checks:
        results[name] = check_func()
    
    # Summary
    print("\n" + "="*60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*60)
    
    all_passed = all(results.values())
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 All checks passed! System ready to run.")
        print("\nStart with paper trading:")
        print("  python main.py")
    else:
        print("\n⚠️  Some checks failed. Please fix issues above before running.")
        sys.exit(1)

if __name__ == "__main__":
    main()
