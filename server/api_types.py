from typing import Annotated
from pydantic import StringConstraints
IDENTIFIER = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
