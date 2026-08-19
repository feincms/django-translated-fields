__version__ = "0.14.0"

from importlib.util import find_spec


if find_spec("django"):
    from translated_fields.admin import *  # noqa: F403
    from translated_fields.fields import *  # noqa: F403
    from translated_fields.utils import *  # noqa: F403
