# This code is a mess.
# This is me learning Python as I go.
# This is not how I write code for my day job.

import tkinter as tk
import socket
import json
import time
from datetime import timedelta
from select import select
from tkinter import ttk
from view_model import *
from PIL import ImageTk, Image, ImageChops
from sys import platform
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--windowed', action='store_true')
args =  parser.parse_args()


LARGEFONT = ("Helvetica", 90)
MED_FONT = ("Helvetica", 70)
SCALE = 1
SPOT_GREEN = "#1DB954"
SPOT_BLACK = "#191414"
SPOT_WHITE = "#FFFFFF"
SPOT_BLUE = "#6d9FFC"

UDP_IP = "127.0.0.1"
UDP_PORT = 9090

DIVIDER_HEIGHT = 3

UP_KEY_CODE = 8320768 if platform == "darwin" else 111
DOWN_KEY_CODE = 8255233 if platform == "darwin" else 116
LEFT_KEY_CODE = 8124162 if platform == "darwin" else 113
RIGHT_KEY_CODE = 8189699 if platform == "darwin" else 114
PREV_KEY_CODE = 2818092 if platform == "darwin" else 0
NEXT_KEY_CODE = 3080238 if platform == "darwin" else 36
PLAY_KEY_CODE = 3211296 if platform == "darwin" else 0

SCREEN_TIMEOUT_SECONDS = 60

wheel_position = -1
last_button = -1

last_interaction = time.time()
screen_on = True


def screen_sleep():
    global screen_on
    screen_on = False
    os.system('xset -display :0 dpms force off')


def screen_wake():
    global screen_on
    screen_on = True
    os.system('xset -display :0 dpms force on')


def flattenAlpha(img, invert=True):
    global SCALE
    [img_w, img_h] = img.size
    img = img.resize((int(img_w * SCALE), int(img_h * SCALE)), Image.ANTIALIAS)
    alpha = img.split()[-1]  # Pull off the alpha layer
    ab = alpha.tobytes()  # Original 8-bit alpha

    checked = []  # Create a new array to store the cleaned up alpha layer bytes

    # Walk through all pixels and set them either to 0 for transparent or 255 for opaque fancy pants
    transparent = 50  # change to suit your tolerance for what is and is not transparent

    p = 0
    for pixel in range(0, len(ab)):
        if (invert and ab[pixel] < transparent) or (not invert and ab[pixel] > 255 - transparent):
            checked.append(0)  # Transparent
        else:
            checked.append(255)  # Opaque
        p += 1

    mask = Image.frombytes('L', img.size, bytes(checked))

    img.putalpha(mask)

    return img


def flatten_alpha(img, color=(255, 255, 255)):
    img = img.convert('RGBA')
    pixdata = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            if pixdata[x, y] == color + (255,):
                pixdata[x, y] = color + (0,)
    return img


class tkinterApp(tk.Tk):

    # __init__ function for class tkinterApp  
    def __init__(self, *args, **kwargs):
        global LARGEFONT, MED_FONT, SCALE
        # __init__ function for class Tk 
        tk.Tk.__init__(self, *args, **kwargs)
        self.geometry("320x240")
        SCALE = 1
        LARGEFONT = ("ChicagoFLF", int(18 * SCALE))
        MED_FONT = ("ChicagoFLF", int(14 * SCALE))
        # creating a container 
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # initializing frames to an empty array 
        self.frames = {}

        # iterating through a tuple consisting 
        # of the different page layouts 
        for F in (StartPage, NowPlayingFrame, SearchFrame):
            frame = F(container, self)

            # initalizing frame of that object from 
            # startpage, page1, page2 respectively with  
            # for loop 
            self.frames[F] = frame

            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(StartPage)

        # to display the current frame passed as

    # parameter
    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()


class Marquee(tk.Canvas):
    def __init__(self, parent, text, margin=0, borderwidth=0, relief='flat', fps=24):
        tk.Canvas.__init__(self, parent, highlightthickness=0, borderwidth=borderwidth, relief=relief,
                           background=SPOT_WHITE)
        self.fps = fps
        self.margin = margin
        self.borderwidth = borderwidth
        # start by drawing the text off screen, then asking the canvas
        # how much space we need. Use that to compute the initial size
        # of the canvas. 
        self.saved_text = text
        self.text = self.create_text(0, -1000, text=text, font=MED_FONT, fill=SPOT_BLACK, anchor="w", tags=("text",))
        (x0, y0, x1, y1) = self.bbox("text")
        self.width = (x1 - x0) + (2 * margin) + (2 * borderwidth)
        self.height = (y1 - y0) + (2 * margin) + (2 * borderwidth)
        self.configure(width=self.width, height=self.height)
        self.reset = True
        self.pause_ctr = 100
        self.after_id = None
        self.redraw()

    def set_text(self, text):
        if (self.saved_text == text):
            return
        self.saved_text = text
        self.itemconfig(self.text, text=text)
        (x0, y0, x1, y1) = self.bbox("text")
        self.width = (x1 - x0) + (2 * self.margin) + (2 * self.borderwidth)
        self.height = (y1 - y0) + (2 * self.margin) + (2 * self.borderwidth)
        self.configure(width=self.width, height=self.height)
        if (self.width > self.winfo_width()):
            self.coords("text", 100, self.winfo_height() / 2)
        else:
            self.coords("text", (self.winfo_width() / 2) - (self.width / 2), self.winfo_height() / 2)
        self.pause_ctr = 100
        self.reset = True
        self.redraw()

    def redraw(self):
        if self.after_id:
            self.after_cancel(self.after_id)
        (x0, y0, x1, y1) = self.bbox("text")
        win_width = self.winfo_width()
        if win_width < 2:
            pass
        elif self.width < win_width:
            self.coords("text", (win_width / 2) - (self.width / 2), self.winfo_height() / 2)
            return
        elif x1 < 0 or y0 < 0 or self.reset:
            self.reset = False
            self.animating = True
            x0 = 20
            y0 = int(self.winfo_height() / 2)
            self.pause_ctr = 100
            self.coords("text", x0, y0)
        elif self.pause_ctr > 0:
            self.pause_ctr = self.pause_ctr - 1
        else:
            self.move("text", -2, 0)
        self.after_id = self.after(int(1000 / self.fps), self.redraw)


class SearchFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.configure(bg=SPOT_WHITE)
        self.header_label = tk.Label(self, text="Search", font=LARGEFONT, background=SPOT_BLUE, foreground=SPOT_WHITE)
        self.header_label.grid(sticky='we', padx=(0, 10))
        self.grid_columnconfigure(0, weight=1)
        divider = tk.Canvas(self)
        divider.configure(bg=SPOT_BLACK, height=DIVIDER_HEIGHT, bd=0, highlightthickness=0, relief='ridge')
        divider.grid(row=1, column=0, sticky="we", pady=(10, int(160 * SCALE)), padx=(0, 0))
        contentFrame = tk.Canvas(self, bg=SPOT_WHITE, highlightthickness=0, relief='ridge')
        contentFrame.grid(row=2, column=0, sticky="nswe")
        self.query_label = tk.Label(contentFrame, text="", font=LARGEFONT, background=SPOT_WHITE, foreground=SPOT_BLACK)
        self.letter_label = tk.Label(contentFrame, text="a", font=LARGEFONT, background=SPOT_BLUE,
                                     foreground=SPOT_WHITE)
        self.query_label.grid(row=0, column=0, sticky="nsw", padx=(120, 0))
        self.letter_label.grid(row=0, column=1, sticky="nsw")
        contentFrame.grid_columnconfigure(1, weight=1)
        search_line = tk.Canvas(self)
        search_line.configure(bg=SPOT_BLACK, height=5, bd=0, highlightthickness=0, relief='ridge')
        search_line.grid(row=3, column=0, sticky="we", pady=10, padx=120)
        self.loading_label = tk.Label(self, text="", font=LARGEFONT, background=SPOT_WHITE, foreground=SPOT_BLACK)
        self.loading_label.grid(row=4, column=0, sticky="we", pady=(int(100 * SCALE), 0))

    def update_search(self, query, active_char, loading):
        self.query_label.configure(text=query)
        self.letter_label.configure(text=active_char)
        loading_text = "Loading..." if loading else ""
        self.loading_label.configure(text=loading_text)


class NowPlayingFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.inflated = False
        self.active = False
        self.update_time = False
        self.configure(bg=SPOT_WHITE)
        self.header_container = Header(self)
        self.header_container.pack(fill='x')
        self.grid_columnconfigure(0, weight=1)
        contentFrame = tk.Canvas(self, bg=SPOT_WHITE, highlightthickness=0, relief='ridge')
        contentFrame.pack()
        self.context_label = tk.Label(contentFrame, text="", font=MED_FONT, background=SPOT_WHITE,
                                      foreground=SPOT_BLACK)
        self.context_label.pack()
        self.artist_label = tk.Label(contentFrame, text="", font=MED_FONT, background=SPOT_WHITE, foreground=SPOT_BLACK)
        self.artist_label.pack()
        self.album_label = tk.Label(contentFrame, text="", font=MED_FONT, background=SPOT_WHITE, foreground=SPOT_BLACK)
        self.album_label.pack()
        self.track_label = Marquee(contentFrame, text="")
        self.track_label.pack()
        # self.progress_frame = tk.Canvas(contentFrame, bg=SPOT_WHITE, highlightthickness=0)
        # self.progress_frame.pack(fill='x', expand=True)
        self.progress_bar = ProgressBar(contentFrame)
        self.progress_bar.pack()
        self.progress_bg_img = ImageTk.PhotoImage(Image.open('progress_background.bmp'))
        self.progress_fg_img = ImageTk.PhotoImage(Image.open('progress_foreground.bmp'))
        self.time_frame = tk.Canvas(contentFrame, bg=SPOT_WHITE, highlightthickness=0)
        self.time_frame.pack()
        self.elapsed_time = tk.Label(self.time_frame, text="00:00", font=LARGEFONT, background=SPOT_WHITE,
                                     foreground=SPOT_BLACK)
        self.elapsed_time.pack()
        self.remaining_time = tk.Label(self.time_frame, text="-00:00", font=LARGEFONT, background=SPOT_WHITE,
                                       foreground=SPOT_BLACK)
        self.remaining_time.pack()
        self.cached_album = None
        self.cached_artist = None

    def update_now_playing(self, now_playing):
        self.header_container.set_text('Now playing')
        # if not self.inflated:
        #     parent_width = self.winfo_width()
        #     if parent_width > 2:
        #         self.midpoint = (parent_width / 2) - 40
        #         self.progress_width = 316
        #         self.progress_start_x = self.midpoint - self.progress_width / 2
        #         self.progress_frame.create_image(0, 0, image=self.progress_bg_img)
        #         self.progress = self.progress_frame.create_image(0, 0, image=self.progress_fg_img)
        #         self.inflated = True
        self.inflated = True
        if not now_playing:
            return
        self.track_label.set_text(now_playing['name'])
        artist = now_playing['artist']
        if self.cached_artist != artist:
            truncd_artist = artist if len(artist) < 20 else artist[0:17] + "..."
            self.artist_label.configure(text=truncd_artist)
            self.cached_artist = artist
        album = now_playing['album']
        if self.cached_album != album:
            truncd_album = album if len(album) < 20 else album[0:17] + "..."
            self.album_label.configure(text=truncd_album)
            self.cached_album = album
        context_name = now_playing['context_name']
        truncd_context = context_name if context_name else "Now Playing"
        truncd_context = truncd_context if len(truncd_context) < 20 else truncd_context[0:17] + "..."
        update_delta = 0 if not now_playing['is_playing'] else (time.time() - now_playing["timestamp"]) * 1000.0
        adjusted_progress_ms = now_playing['progress'] + update_delta
        adjusted_remaining_ms = max(0, now_playing['duration'] - adjusted_progress_ms)
        if self.update_time:
            progress_txt = ":".join(str(timedelta(milliseconds=adjusted_progress_ms)).split('.')[0].split(':')[1:3])
            remaining_txt = "-" + ":".join(
                str(timedelta(milliseconds=adjusted_remaining_ms)).split('.')[0].split(':')[1:3])
            self.elapsed_time.configure(text=progress_txt)
            self.remaining_time.configure(text=remaining_txt)
        self.update_time = not self.update_time
        if self.inflated:
            self.progress_bar.set_progress(min(1.0, adjusted_progress_ms / now_playing['duration']))
            # self.progress_frame.coords(self.progress, self.progress_start_x, 0, self.progress_width * adjusted_progress_pct + self.progress_start_x, int(72 * SCALE))
        if (now_playing['track_index'] < 0):
            self.context_label.configure(text="")
            return
        context_str = str(now_playing['track_index']) + " of " + str(now_playing['track_total'])
        self.context_label.configure(text=context_str)


class ProgressBar(tk.Canvas):
    def __init__(self, parent):
        tk.Canvas.__init__(self, parent, bg=SPOT_WHITE, highlightthickness=0, width=316, height=11)
        self.progress_bg_img = ImageTk.PhotoImage(Image.open('progress_background.bmp'))
        self.progress_fg_img = ImageTk.PhotoImage(Image.open('progress_foreground.bmp'))
        self.create_image(0, 0, image=self.progress_bg_img, anchor='nw')
        self.progress_fg = tk.Canvas(self, bg=SPOT_BLACK, highlightthickness=0, width=50, height=11 * SCALE)
        self.progress_fg.create_image(0, 0, image=self.progress_fg_img, anchor='nw')
        self.progress_fg.place(x=0, y=0)

    def set_progress(self, percentage):
        self.progress_fg.configure(width=percentage * 316)


class GradiantCanvas(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.gradiant = []

    def clear_gradiant(self):
        for line in self.gradiant:
            self.delete(line)
        self.gradiant = []

    def set_gradiant(self, start, end):
        if not len(self.gradiant):
            self.gradiant = []
            (r1, g1, b1) = self.winfo_rgb(start)
            (r2, g2, b2) = self.winfo_rgb(end)
            r_ratio = float(r2 - r1) / self.winfo_height()
            g_ratio = float(g2 - g1) / self.winfo_height()
            b_ratio = float(b2 - b1) / self.winfo_height()
            for i in range(self.winfo_height()):
                nr = int(r1 + (r_ratio * i))
                ng = int(g1 + (g_ratio * i))
                nb = int(b1 + (b_ratio * i))
                color = "#%4.4x%4.4x%4.4x" % (nr, ng, nb)
                line = self.create_line(0, i, self.winfo_width(), i, fill=color)
                self.tag_lower(line)
                self.gradiant.append(line)


class ListItem(GradiantCanvas):
    def __init__(self, parent):
        GradiantCanvas.__init__(self, parent, bg=SPOT_WHITE, height=24, highlightthickness=0)
        self.black_arrow_image = ImageTk.PhotoImage(Image.open('carret_black.bmp'))
        self.white_arrow_image = ImageTk.PhotoImage(
            flatten_alpha(ImageChops.invert(Image.open('carret_black.bmp')), color=(0, 0, 0)))
        self.empty_arrow_image = ImageTk.PhotoImage(Image.open('pod_arrow_empty.png'))
        self.gradiant = []
        self.text = self.create_text(6, 12, text='Text', font=MED_FONT, anchor='w',
                                     fill=SPOT_BLACK)
        self.arrow_image = self.create_image(0, 0, image=self.empty_arrow_image)

    def set_list_item(self, text, line_type=LINE_NORMAL, show_arrow=False):
        # self.update_idletasks()
        bgColor = SPOT_BLUE if line_type == LINE_HIGHLIGHT else SPOT_WHITE
        txtColor = SPOT_WHITE if line_type == LINE_HIGHLIGHT else \
            (SPOT_BLACK if line_type == LINE_NORMAL else SPOT_WHITE)
        truncd_text = text if len(text) < 17 else text[0:15] + "..."
        # self.listItems[index].configure(bg = bgColor)
        arrowImg = self.empty_arrow_image if not show_arrow else \
            (self.white_arrow_image if line_type == LINE_HIGHLIGHT else self.black_arrow_image)
        if line_type == LINE_HIGHLIGHT:
            self.set_gradiant(start="#72a5dc", end="#4188e4")
        else:
            self.clear_gradiant()

        self.itemconfig(self.text, text=truncd_text, fill=txtColor)

        # self.delete(self.arrow_image)
        # self.arrow_image = self.create_image(self.winfo_width() - 6, self.winfo_height() / 2, image=arrowImg,
        #                                      anchor='e')


class Header(GradiantCanvas):
    def __init__(self, parent):
        GradiantCanvas.__init__(self, parent, bg=SPOT_WHITE, height=24, highlightthickness=0)
        self.text = None

    def set_text(self, text='', now_playing=None, has_wifi=False):
        # self.space_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_space.png')))
        # self.play_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_play.png')))
        # self.pause_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_pause.png')))
        # self.wifi_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_wifi.png')))
        text = text if len(text) < 20 else text[0:17] + "..."
        # play_image = self.space_image
        # if now_playing is not None:
        #     play_image = self.play_image if now_playing['is_playing'] else self.pause_image
        # wifi_image = self.wifi_image if has_wifi else self.space_image
        self.update_idletasks()

        if not self.text:
            self.update_idletasks()
            self.text = self.create_text(self.winfo_width() / 2, self.winfo_height() / 2, text=text, font=MED_FONT,
                                         fill=SPOT_BLACK)
        else:
            self.itemconfig(self.text, text=text)
        self.set_gradiant(start="#f6f6ff", end="#c5cacd")


class Scrollbar(tk.Canvas):
    def __init__(self, parent):
        tk.Canvas.__init__(self, parent, bg=SPOT_WHITE, width=int(11 * SCALE), highlightthickness=0)
        self.scrollbar_container_image = ImageTk.PhotoImage(Image.open('scrollbar_container_long.bmp'))
        self.scrollbar_image = ImageTk.PhotoImage(Image.open('scrollbar_long.bmp'))
        self.create_image(0, 0, image=self.scrollbar_container_image, anchor='nw')
        self.scrollbar = tk.Canvas(self, bg=SPOT_BLACK, highlightthickness=0, width=int(11 * SCALE), height=50)
        self.scrollbar.create_image(0, 0, image=self.scrollbar_image, anchor='nw')
        self.scrollbar.pack()
        self.initialized = False

    def show_scroll(self, index, total_count):
        scroll_bar_y_rel_size = max(0.9 - (total_count - MENU_PAGE_SIZE) * 0.06, 0.03)
        scroll_bar_y_raw_size = scroll_bar_y_rel_size * self.winfo_height()
        percentage = index / (total_count - MENU_PAGE_SIZE)
        if not self.initialized:
            self.scrollbar.configure(height=scroll_bar_y_raw_size)
            self.initialized = True
        self.scrollbar.place(x=0, y=percentage * (216 - scroll_bar_y_raw_size))


class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.scrollbar_container_image = ImageTk.PhotoImage(Image.open('scrollbar_container.bmp'))
        self.scrollbar_image = ImageTk.PhotoImage(Image.open('scrollbar.bmp'))
        self.configure(bg=SPOT_WHITE)
        self.header = Header(self)
        self.header.pack(fill='x')

        contentFrame = tk.Canvas(self, bg=SPOT_GREEN, highlightthickness=0, relief='ridge')
        contentFrame.pack(fill='both')

        self.grid_rowconfigure(2, weight=1)
        listFrame = tk.Canvas(contentFrame)
        listFrame.configure(bg=SPOT_WHITE, bd=0, highlightthickness=0)
        listFrame.grid(row=0, column=0, sticky="nsew")
        contentFrame.grid_rowconfigure(0, weight=1)
        contentFrame.grid_columnconfigure(0, weight=1)

        # scrollbar 
        self.scrollFrame = Scrollbar(contentFrame)
        self.scrollFrame.grid(row=0, column=1, sticky="ns")

        self.listItems = []
        self.arrows = []
        for x in range(9):
            item = ListItem(listFrame)
            self.listItems.append(item)
            item.pack(fill='x', padx=0, pady=0)
        listFrame.grid_columnconfigure(0, weight=1)


def processInput(app, input):
    global wheel_position, last_button, last_interaction
    position = input[2]
    button = input[0]
    button_state = input[1]
    if button == 29 and button_state == 0:
        wheel_position = -1
    elif wheel_position == -1:
        wheel_position = position
    elif position % 2 != 0:
        pass
    elif wheel_position <= 1 and position > 44:
        onDownPressed()
        wheel_position = position
    elif wheel_position >= 44 and position < 1:
        onUpPressed()
        wheel_position = position
    elif abs(wheel_position - position) > 6:
        wheel_position = -1
    elif wheel_position > position:
        onDownPressed()
        wheel_position = position
    elif wheel_position < position:
        onUpPressed()
        wheel_position = position

    if button_state == 0:
        last_button = -1
    elif button == last_button:
        pass
    elif button == 7:
        onSelectPressed()
        last_button = button
    elif button == 11:
        onBackPressed()
        last_button = button
    elif button == 10:
        onPlayPressed()
        last_button = button
    elif button == 8:
        onNextPressed()
        last_button = button
    elif button == 9:
        onPrevPressed()
        last_button = button

    now = time.time()
    if (now - last_interaction > SCREEN_TIMEOUT_SECONDS):
        print("waking")
        screen_wake()
    last_interaction = now


def onKeyPress(event):
    c = event.keycode
    if (c == UP_KEY_CODE):
        onUpPressed()
    elif (c == DOWN_KEY_CODE):
        onDownPressed()
    elif (c == RIGHT_KEY_CODE):
        onSelectPressed()
    elif (c == LEFT_KEY_CODE):
        onBackPressed()
    elif (c == NEXT_KEY_CODE):
        onNextPressed()
    elif (c == PREV_KEY_CODE):
        onPrevPressed()
    elif (c == PLAY_KEY_CODE):
        onPlayPressed()
    else:
        print("unrecognized key: ", c)


def update_search(q, ch, loading, results):
    global app, page
    search_page = app.frames[SearchFrame]
    if (results is not None):
        page.render().unsubscribe()
        page = SearchResultsPage(page, results)
        render(app, page.render())
    else:
        search_page.update_search(q, ch, loading)


def render_search(app, search_render):
    app.show_frame(SearchFrame)
    search_render.subscribe(app, update_search)


def render_menu(app, menu_render):
    # app.show_frame(StartPage)
    page = app.frames[StartPage]
    if (menu_render.total_count > MENU_PAGE_SIZE):
        page.scrollFrame.show_scroll(menu_render.page_start, menu_render.total_count)
    # else:
    #     page.scrollFrame.hide_scroll()
    for (i, line) in enumerate(menu_render.lines):
        page.listItems[i].set_list_item(text=line.title, line_type=line.line_type, show_arrow=line.show_arrow)
    page.header.set_text(menu_render.header, menu_render.now_playing, menu_render.has_internet)


def update_now_playing(now_playing):
    frame = app.frames[NowPlayingFrame]
    frame.update_now_playing(now_playing)


def render_now_playing(app, now_playing_render):
    app.show_frame(NowPlayingFrame)
    now_playing_render.subscribe(app, update_now_playing)


def render(app, render):
    if (render.type == MENU_RENDER_TYPE):
        render_menu(app, render)
    elif (render.type == NOW_PLAYING_RENDER):
        render_now_playing(app, render)
    elif (render.type == SEARCH_RENDER):
        render_search(app, render)


def onPlayPressed():
    global page, app
    page.nav_play()
    render(app, page.render())


def onSelectPressed():
    global page, app
    if (not page.has_sub_page):
        return
    page.render().unsubscribe()
    page = page.nav_select()
    render(app, page.render())


def onBackPressed():
    global page, app
    previous_page = page.nav_back()
    if (previous_page):
        page.render().unsubscribe()
        page = previous_page
        render(app, page.render())


def onNextPressed():
    global page, app
    page.nav_next()
    render(app, page.render())


def onPrevPressed():
    global page, app
    page.nav_prev()
    render(app, page.render())


def onUpPressed():
    global page, app
    page.nav_up()
    render(app, page.render())


def onDownPressed():
    global page, app
    page.nav_down()
    render(app, page.render())


# Driver Code 
page = RootPage(None)
app = tkinterApp()
render(app, page.render())
app.overrideredirect(True)
app.overrideredirect(False)
app.attributes('-fullscreen', not args.windowed)
sock = socket.socket(socket.AF_INET,  # Internet
                     socket.SOCK_DGRAM)  # UDP
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(0)
socket_list = [sock]
loop_count = 0


def app_main_loop():
    global app, page, loop_count, last_interaction, screen_on
    try:
        read_sockets = select(socket_list, [], [], 0)[0]
        for socket in read_sockets:
            data = socket.recv(128)
            processInput(app, data)
        loop_count += 1
        if (loop_count >= 300):
            if (time.time() - last_interaction > SCREEN_TIMEOUT_SECONDS and screen_on):
                screen_sleep()
            # render(app, page.render())
            loop_count = 0
    except:
        pass
    finally:
        app.after(2, app_main_loop)


app.bind('<KeyPress>', onKeyPress)
app.after(5, app_main_loop)
app.mainloop()
