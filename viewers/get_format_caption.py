def get_format_caption(caption: str):
    caption_split = caption.split("\n")
    caption_split[0] = f"<b>{caption_split[0]}</b>"
    caption_res = "\n".join(caption_split)
    return caption_res