from dataclasses import dataclass
from typing import Any

from ..abc import AbstractLineAction


@dataclass(frozen=True)
class QuickReplyButton:
    """This is a quick reply option that is displayed as a button.

    Args:
        action (:obj:`AbstractLineAction`): Action performed when this button is tapped.
            Specify an action object. The following is a list of the available actions:
            * Postback action
            * Message action
            * URI action
            * Datetime picker action
            * Camera action
            * Camera roll action
            * Location action
        image_url (str, optional): URL of the icon that is displayed at the
            beginning of the button
            Max character limit: 2000
            URL scheme: ``https``
            Image format: PNG
            Aspect ratio: ``1:1`` (width : height)
            Data size: Up to 1 MB
            There is no limit on the image size.
            If the action property has a camera action, camera roll action, or
            location action, and ``image_url`` is not set, the default icon is
            displayed. The URL should be percent-encoded using UTF-8.
    """

    action: AbstractLineAction | dict
    image_url: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "type": "action",
            "action": self.action.to_json()
            if isinstance(self.action, AbstractLineAction)
            else self.action,
            "imageUrl": self.image_url,
        }
