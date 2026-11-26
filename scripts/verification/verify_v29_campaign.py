"""Offline phase-three acceptance with all preceding v29 regressions."""
from verify_v29_actor import main


if __name__ == '__main__':
    main(include_method=True, include_campaign=True)
