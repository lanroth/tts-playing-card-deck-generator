#!/usr/bin/env python3

import argparse
import os
import sys

from PIL import Image, ImageDraw

args = None
template_im: Image = None

cols, rows = 10, 7

card_number_width = 58
card_number_height = 150


def init():
    global args, template_im
    parser = argparse.ArgumentParser(
        description='create Tabletop Simulator compatible card deck from template and image files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-t', '--template', default='card_template.png', help='deck template image')
    parser.add_argument('-o', '--out', default='card_deck.png', help='the generated image file to write')
    parser.add_argument('input', type=str, nargs='+', help='files and directories to look for source images')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='recurse directories when looking for source images')
    parser.add_argument('-a', '--aspect-ratio-tolerance', default=0,
                        help='1 = aspect ratios must be exact match, 0 = any aspect ratio')
    parser.add_argument('-H', '--hidden-card', help='image to use for the face of a card that is hidden')
    parser.add_argument('--display-deck', action='store_true', help='display the generated deck image on screen')
    parser.add_argument('--deck-size', type=int, default=52, help='number of cards in deck')
    parser.add_argument('-d', '--debug', action='store_true', help='print lots of debug output')
    args = parser.parse_args()

    template_im = Image.open(args.template)


def debug(msg):
    if args.debug:
        print(msg)


def get_card(im, pos):
    card_width = im.size[0] // cols
    card_height = im.size[1] // rows

    x = (pos % cols)
    y = (pos // cols)

    return im.crop((
        x * card_width,
        y * card_height,
        x * card_width + card_width,
        y * card_height + card_height))


def extract_card_number(im: Image) -> Image:
    im = im.convert('RGBA')
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, card_number_height, im.width - card_number_width, im.height), fill=(0, 0, 0, 0))
    draw.rectangle((card_number_width, 0, im.width, im.height - card_number_height), fill=(0, 0, 0, 0))
    return im


def is_aspect_ratio_in_tolerance(card_size: tuple, im_size: tuple, tolerance: float) -> bool:
    c_width, c_height = card_size
    im_width, im_height = im_size
    c_ar = c_width / c_height
    im_ar = im_width / im_height
    return (c_ar / im_ar >= tolerance) and (im_ar / c_ar >= tolerance)


def add_file_if_good(selected_images, path):
    try:
        im = Image.open(path)
        if is_aspect_ratio_in_tolerance(template_im.size, im.size, args.aspect_ratio_tolerance):
            debug(f"good aspect ratio: {path}")
            selected_images.append(path)
        else:
            debug(f" bad aspect ratio: {path}")
    except Exception as e:
        print(f'failed to read {path}: {e}')


def select_images():
    selected_images = []

    for path in args.input:
        if os.path.isdir(path):
            debug(f'reading dir: {path}')

            for dir_name, subdir_list, file_list in os.walk(path):
                debug('in directory: %s' % dir_name)
                for fname in file_list:
                    debug('\t%s' % fname)
                    add_file_if_good(selected_images, os.path.join(dir_name, fname))
                    if len(selected_images) > args.deck_size:
                        return selected_images

                if not args.recursive:
                    break

        elif os.path.isfile(path):
            debug(f'reading file: {path}')
            add_file_if_good(selected_images, path)
            if len(selected_images) > args.deck_size:
                return selected_images

        else:
            print(f"ignoring {path}: is neither file or dir.")

    return selected_images


def crop_center(pil_img, crop_size):
    crop_width, crop_height = crop_size
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))


def resize_and_crop(im, size):
    w, h = size

    im_aspect_ratio = im.width / im.height
    card_aspect_ratio = w / h

    if im_aspect_ratio > card_aspect_ratio:
        shrink_factor = im.height / h
        new_width = round(im.width / shrink_factor)
        im = im.resize((new_width, h))
    else:
        shrink_factor = im.width / w
        new_height = round(im.height / shrink_factor)
        im = im.resize((w, new_height))

    return crop_center(im, size)


def add_image(card, image_filename):
    im = Image.open(image_filename)
    im = resize_and_crop(im, card.size)
    im = im.convert('RGBA')
    return Image.alpha_composite(im, card)


def replace_card(im: Image, card: Image, pos: int) -> None:
    im.paste(card, (card.width * (pos % 10), card.height * (pos // 10)))


def main():
    init()

    image_filenames = select_images()

    if not image_filenames:
        print('failed to load any images.')
        sys.exit(-1)

    for i in range(0, args.deck_size):
        card = extract_card_number(get_card(template_im, i))
        card = add_image(card, image_filenames[i % len(image_filenames)])
        replace_card(template_im, card, i)

    try:
        hidden_card = Image.open(args.hidden_card)
        hidden_card = resize_and_crop(hidden_card, card.size)

        replace_card(template_im, hidden_card, 69)

    except AttributeError:
        pass

    template_im.save(args.out, optimize=True)
    if args.display_deck:
        template_im.show()


if __name__ == '__main__':
    main()
