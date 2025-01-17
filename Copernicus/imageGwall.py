"""
#    fabulous.imageGwall
    ~~~~~~~~~~~~~~

"""

import sys
import itertools
import subprocess

import grapefruit as gf

from fabulous import utils, xterm256


class Image(object):
    """Printing image files to a terminal

    I use :mod:`PIL` to turn your image file into a bitmap, resize it
    so it'll fit inside your terminal, and implement methods so I can
    behave like a string or iterable.

    When resizing, I'll assume that a single character on the terminal
    display is one pixel wide and two pixels tall.  For most fonts
    this is the best way to preserve the aspect ratio of your image.

    All colors are are quantized by :mod:`fabulous.xterm256` to the
    256 colors supported by modern terminals.  When quantizing
    semi-transparant pixels (common in text or PNG files) I'll ask
    :class:`TerminalInfo` for the background color I should use to
    solidify the color.  Fully transparent pixels will be rendered as
    a blank space without color so we don't need to mix in a
    background color.

    I also put a lot of work into optimizing the output line-by-line
    so it needs as few ANSI escape sequences as possible.  If your
    terminal is kinda slow, you're gonna want to buy me a drink ;) You
    can use :class:`DebugImage` to visualize these optimizations.

    The generated output will only include spaces with different
    background colors.  In the future routines will be provided to
    overlay text on top of these images.

    """

    pad = ' '
#    pad = 'MMMMMMMMMMMAAAAOOOOOOOOOOWWWWW'

    def __init__(self, path, width=None):
        utils.pil_check()
        from PIL import Image as PillsPillsPills
        self.img = PillsPillsPills.open(path)
        # when reading pixels, gifs will return colors corresponding
        # to a palette if we don't do this :\
        self.img = self.img.convert("RGBA")
        self.resize(width)

    def __iter__(self):
        """I allow Image to behave as an iterable

        By using me with a for loop, you can use each line as they're
        created.  When printing a large image, this helps you not have
        to wait for the whole thing to be converted.

        :return: Yields lines of text (without line end character)
        """
        # strip out blank lines
        Taille = int(subprocess.check_output(['stty', 'size']).split()[1])
        Taille = Taille / 4
        placehold ="".center(int(Taille))
        for line in self.reduce(self.convert()):
            if line.strip():
                print((placehold , line))
        yield ""

    def __str__(self):
        """I return the entire image as one big string

        Unlike the iteration approach, you have to wait for the entire
        image to be converted.

        :return: String containing all lines joined together.
        """
        return "\n".join(self)

    @property
    def size(self):
        """Returns size of image
        """
        return self.img.size

    def resize(self, width=None):
        """Resizes image to fit inside terminal

        Called by the constructor automatically.
        """
        (iw, ih) = self.size
        if width is None:
            width = min(iw, utils.term.width)
            width = width / 2
        elif isinstance(width, str):
            percents = dict([(pct, '%s%%' % (pct)) for pct in range(101)])
            width = percents[width]
        height = int(float(ih) * (float(width) / float(iw)))
        height //= 2
        self.img = self.img.resize((int(width), int(height)))

    def reduce(self, colors):
        """Converts color codes into optimized text

        This optimizer works by merging adjacent colors so we don't
        have to repeat the same escape codes for each pixel.  There is
        no loss of information.

        :param colors: Iterable yielding an xterm color code for each
                       pixel, None to indicate a transparent pixel, or
                       ``'EOL'`` to indicate th end of a line.

        :return: Yields lines of optimized text.

        """
        need_reset = False
        line = []
        for color, items in itertools.groupby(colors):
            if color is None:
                if need_reset:
                    line.append("\x1b[49m")
                    need_reset = False
                line.append(self.pad * len(list(items)))
            elif color == "EOL":
                if need_reset:
                    line.append("\x1b[49m")
                    need_reset = False
                    yield "".join(line)
                else:
                    line.pop()
                    yield "".join(line)
                line = []
            else:
                need_reset = True
                line.append("\x1b[48;5;%dm%s" % (
                    color, self.pad * len(list(items))))

    def convert(self):
        """Yields xterm color codes for each pixel in image
        """
        (width, height) = self.img.size
        bgcolor = utils.term.bgcolor
        self.img.load()
        for y in range(height):
            for x in range(width):
                rgba = self.img.getpixel((x, y))
                if len(rgba) == 4 and rgba[3] == 0:
                    yield None
                elif len(rgba) == 3 or rgba[3] == 255:
                    yield xterm256.rgb_to_xterm(*rgba[:3])
                else:
                    color = gf.Color.NewFromRgb(*[c / 255.0 for c in rgba])
                    rgba = gf.Color.AlphaBlend(color, bgcolor).rgb
                    yield xterm256.rgb_to_xterm(
                        *[int(c * 255.0) for c in rgba])
            yield "EOL"


def main(args):
    """I provide a command-line interface for this module
    """
    Taille = int(subprocess.check_output(['stty', 'size']).split()[1])
    Taille = Taille / 4
    print(Taille)
    for imgpath in args:
        for line in Image(imgpath):
                 placehold ="".center(Taille)
                 print((placehold + line))


if __name__ == '__main__':
    main(sys.argv[1:])
