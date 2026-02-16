try:
    import pywizlight
    print(f"pywizlight imported successfully. Version: {getattr(pywizlight, '__version__', 'unknown')}")
    from pywizlight import wizlight, PilotBuilder
    print("Classes imported.")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
