import ascii_magic


def image_to_ascii(image_url: str):
    """
    Convert an image from the given URL to ASCII art and display it in the terminal.

    Args:
        image_url (str): The URL of the image to convert.

    Returns:
        None: The ASCII art is displayed in the terminal.

    Raises:
        AsciiMagicError: If an error occurs while converting the image.

    Example:
        >>> image_to_ascii("https://example.com/image.jpg")

    """
    img = ascii_magic.from_url(image_url, columns=30)
    ascii_magic.to_terminal(img)
