"""Run the test-set loader: python load_test_set.py [path/to/test_set.csv]"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from ecc_intake_schema.loader import main  # noqa: E402

sys.exit(main())
