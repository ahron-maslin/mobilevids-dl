import ascii_magic


def image_to_ascii(image_url: str):
    img = ascii_magic.from_url(image_url, columns=30)
    ascii_magic.to_terminal(img)