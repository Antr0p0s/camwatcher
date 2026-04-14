import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Button, TextBox, Slider

class LiveUI:
    def __init__(self, initial_image, img_lims):
        plt.ion()
        dpi = 100

        # 1. Get dimensions
        h, w = initial_image.shape

        # 2. Figure sizing logic
        max_dim = 14.0
        if w > h:
            figsize = (max_dim, max_dim * (h / w) + 4.0)
        else:
            figsize = (max(5.0, max_dim * (w / h)), max_dim + 2.5)

        self.fig, self.ax = plt.subplots(figsize=figsize, dpi=dpi)

        # 3. Layout: Leave space at bottom for buttons and right for sliders
        plt.subplots_adjust(bottom=0.25, right=0.85)

        self.vmin = img_lims[0]
        self.vmax = img_lims[1]
        
        # Set slider max range (adjust to 4095 if using 12-bit, or 65535 for 16-bit)
        self.slider_max = self.vmax * 2.5 

        self.ax.set_xlim(0, w)
        self.ax.set_ylim(h, 0)

        self.im = self.ax.imshow(
            initial_image,
            cmap="gray",
            vmin=self.vmin,
            vmax=self.vmax,
            aspect="equal",
        )

        self.filename = "auto_upload_test"
        self._build_ui()

    def _build_ui(self):
        # ---- Start/Stop Button ----
        self.ax_start = plt.axes([0.35, 0.12, 0.3, 0.075])
        self.btn_toggle = Button(
            self.ax_start,
            "Start recording",
            color="#e1e1e1",
            hovercolor="#ffd700",
        )

        # ---- Filename TextBox ----
        self.ax_text = plt.axes([0.25, 0.02, 0.5, 0.06])
        self.text_box = TextBox(
            self.ax_text,
            "Filename:",
            initial=self.filename
        )
        self.text_box.on_submit(self._update_filename)

        # ---- Vertical Contrast Sliders (Right Side) ----
        # Coordinates: [left, bottom, width, height]
        ax_vmax = plt.axes([0.88, 0.25, 0.02, 0.6]) 
        ax_vmin = plt.axes([0.93, 0.25, 0.02, 0.6])

        self.slider_vmax = Slider(
            ax=ax_vmax,
            label="Vmax ",
            valmin=0,
            valmax=self.slider_max,
            valinit=self.vmax,
            orientation="vertical",
            valfmt="%d",
            color="#ff4d4d" # Reddish for highlights
        )

        self.slider_vmin = Slider(
            ax=ax_vmin,
            label="Vmin ",
            valmin=0,
            valmax=self.slider_max,
            valinit=self.vmin,
            orientation="vertical",
            valfmt="%d",
            color="#3399ff" # Bluish for blacks
        )

        # Connect slider events
        self.slider_vmax.on_changed(self._update_contrast)
        self.slider_vmin.on_changed(self._update_contrast)

    def _update_contrast(self, val):
        """Callback triggered when sliders move."""
        self.vmin = self.slider_vmin.val
        self.vmax = self.slider_vmax.val
        
        # Clip logic to prevent vmin > vmax
        if self.vmin >= self.vmax:
            self.vmax = self.vmin + 1
            
        self.im.set_clim(self.vmin, self.vmax)
        self.fig.canvas.draw_idle()

    def _update_filename(self, text):
        text = text.strip()
        if text != "":
            self.filename = text

    def get_filename(self):
        return self.filename
    
    def get_img_lims(self):
        return [self.vmin, self.vmax]

    def update_image(self, image):
        """Standard update loop for live feed."""
        if self.im is not None:
            self.im.set_data(image)
            # Ensure the contrast settings from sliders are applied to the new frame
            self.im.set_clim(self.vmin, self.vmax)
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()

    def set_title(self, text):
        self.ax.set_title(text)

    def set_sub_title(self, text):
        self.fig.suptitle(text, fontsize=10, y=0.97, verticalalignment="top")

    def toggle_preview_artist(self, image):
        """Removes or recreates the image artist (e.g. for pause/resume)."""
        if self.im is not None:
            self.im.remove()
            self.im = None
        else:
            self.im = self.ax.imshow(
                np.zeros_like(image),
                cmap="gray",
                vmin=self.vmin,
                vmax=self.vmax,
                aspect="equal",
            )

    def exists(self):
        return plt.fignum_exists(self.fig.number)

    def close(self):
        plt.ioff()
        plt.close(self.fig)