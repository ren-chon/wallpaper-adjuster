#!/usr/bin/env python3

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, GdkPixbuf
import subprocess
import os
# import asyncio
from concurrent.futures import ThreadPoolExecutor

APP_ID = "com.renchon.wallpaper-adjuster"
VERSION = "1.0.0"
GITHUB_USER = "ren-chon"
TWITTER_USER = "prod_ocean"


class MainWindow(Adw.ApplicationWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_title("Wallpaper Adjuster")
        self.set_default_size(400, 600)

        header = Adw.HeaderBar()
        menu_button = Gtk.MenuButton()
        menu = Gio.Menu()
        menu.append("About", "app.about")
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        self.toast_overlay = Adw.ToastOverlay()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(header)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)

        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                               spacing=12)

        header_label = Gtk.Label()
        header_label.set_markup("<b>Wallpaper Settings</b>")
        settings_box.append(header_label)

        fitting_group = Adw.PreferencesGroup()
        fitting_group.set_title("Fitting Options")
        settings_box.append(fitting_group)

        self.fitting_options = {
            # 'Original Size': 'none',
            'Tiled': 'wallpaper',
            'Centered': 'centered',
            'Scaled (Fit)': 'scaled',
            'Zoom (Fill)': 'zoom',
            'Spanned': 'spanned'
        }

        self.combo = Gtk.DropDown.new_from_strings(
            list(self.fitting_options.keys()))
        self.combo.connect('notify::selected', self.on_setting_changed)
        fitting_group.add(self.combo)

        additional_group = Adw.PreferencesGroup()
        additional_group.set_title("Additional Options")
        settings_box.append(additional_group)

        self.color_button = Gtk.ColorButton()
        self.color_button.set_title("Select Background Color")
        self.color_button.connect('color-set', self.on_setting_changed)
        color_row = Adw.ActionRow()
        color_row.set_title("Background Color")
        color_row.set_subtitle("Color shown when image doesn't fill screen")
        color_row.add_suffix(self.color_button)
        additional_group.add(color_row)

        brightness_row = Adw.ActionRow()
        brightness_row.set_title("Brightness")
        self.brightness_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        self.brightness_scale.set_value(100)
        self.brightness_scale.set_hexpand(True)
        self.brightness_scale.connect('value-changed', self.on_setting_changed)
        brightness_row.add_suffix(self.brightness_scale)
        additional_group.add(brightness_row)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(12)

        self.spinner = Gtk.Spinner()
        button_box.append(self.spinner)

        self.apply_button = Gtk.Button(label="Apply")
        self.apply_button.connect('clicked', self.on_apply_clicked)
        button_box.append(self.apply_button)

        settings_box.append(button_box)

        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        preview_box.set_vexpand(True)

        preview_label = Gtk.Label()
        preview_label.set_markup("<b>Preview</b>")
        preview_box.append(preview_label)

        preview_frame = Gtk.Frame()
        preview_frame.set_vexpand(True)

        self.preview_area = Gtk.DrawingArea()
        self.preview_area.set_draw_func(self.draw_preview)
        self.preview_area.set_vexpand(True)
        self.preview_area.set_content_width(300)
        self.preview_area.set_content_height(200)
        preview_frame.set_child(self.preview_area)
        preview_box.append(preview_frame)

        content_box.append(settings_box)
        content_box.append(preview_box)

        self.toast_overlay.set_child(content_box)
        main_box.append(self.toast_overlay)
        self.set_content(main_box)

        self.load_current_settings()

        self.executor = ThreadPoolExecutor(max_workers=1)

    def load_current_settings(self):
        try:
            current_option = subprocess.check_output([
                'gsettings', 'get', 'org.gnome.desktop.background',
                'picture-options'
            ]).decode().strip().replace("'", "")

            for i, (key, value) in enumerate(self.fitting_options.items()):
                if value == current_option:
                    self.combo.set_selected(i)
                    break

            color = subprocess.check_output([
                'gsettings', 'get', 'org.gnome.desktop.background',
                'primary-color'
            ]).decode().strip().replace("'", "")
            rgba = Gdk.RGBA()
            rgba.parse(color)
            self.color_button.set_rgba(rgba)

            brightness = float(
                subprocess.check_output([
                    'gsettings', 'get', 'org.gnome.desktop.background',
                    'picture-opacity'
                ]).decode().strip()) * 100
            self.brightness_scale.set_value(brightness)

        except (subprocess.CalledProcessError, ValueError) as e:
            self.show_toast(f"Error loading current settings: {str(e)}", False)

    # Scuffed preview
    def draw_preview(self, area, cr, width, height):
        try:
            wallpaper_path = subprocess.check_output([
                'gsettings', 'get', 'org.gnome.desktop.background',
                'picture-uri-dark'
            ]).decode().strip().replace("'", "").replace("file://", "")

            # Get selected fitting option
            selected_text = self.combo.get_selected_item().get_string()
            fitting = self.fitting_options[selected_text]

            # Draw background color
            color = self.color_button.get_rgba()
            cr.set_source_rgb(color.red, color.green, color.blue)
            cr.rectangle(0, 0, width, height)
            cr.fill()

            # Load and draw wallpaper
            if os.path.exists(wallpaper_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(wallpaper_path)

                # Apply brightness
                brightness = self.brightness_scale.get_value() / 100
                if brightness != 1.0:
                    pixbuf = pixbuf.copy()
                    pixbuf.saturate_and_pixelate(pixbuf, brightness, False)

                # Calculate dimensions based on fitting option
                image_width = pixbuf.get_width()
                image_height = pixbuf.get_height()

                # Calculate aspect ratios
                image_aspect = image_width / image_height
                preview_aspect = width / height

                if fitting == 'none':
                    # Original size - scale down if too large
                    scale = min(1.0, width / image_width,
                                height / image_height)
                    new_width = image_width * scale
                    new_height = image_height * scale
                    x = (width - new_width) / 2
                    y = (height - new_height) / 2
                    cr.save()
                    cr.translate(x, y)
                    cr.scale(scale, scale)
                    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
                    cr.paint_with_alpha(brightness)
                    cr.restore()

                elif fitting == 'centered':
                    # Centered - scale down if too large
                    scale = min(1.0, width / image_width,
                                height / image_height)
                    new_width = image_width * scale
                    new_height = image_height * scale
                    x = (width - new_width) / 2
                    y = (height - new_height) / 2
                    cr.save()
                    cr.translate(x, y)
                    cr.scale(scale, scale)
                    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
                    cr.paint_with_alpha(brightness)
                    cr.restore()

                elif fitting == 'scaled':
                    # Scaled (Fit) - preserve aspect ratio
                    scale = min(width / image_width, height / image_height)
                    new_width = image_width * scale
                    new_height = image_height * scale
                    x = (width - new_width) / 2
                    y = (height - new_height) / 2
                    cr.save()
                    cr.translate(x, y)
                    cr.scale(scale, scale)
                    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
                    cr.paint_with_alpha(brightness)
                    cr.restore()

                elif fitting == 'zoom':
                    # Zoom (Fill) - preserve aspect ratio, crop if needed
                    scale = max(width / image_width, height / image_height)
                    new_width = image_width * scale
                    new_height = image_height * scale
                    x = (width - new_width) / 2
                    y = (height - new_height) / 2
                    cr.save()
                    cr.translate(x, y)
                    cr.scale(scale, scale)
                    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
                    cr.paint_with_alpha(brightness)
                    cr.restore()

                elif fitting == 'wallpaper':
                    # Tiled - scale tiles to reasonable size
                    tile_scale = min(width / image_width / 2,
                                     height / image_height / 2)
                    tile_width = image_width * tile_scale
                    tile_height = image_height * tile_scale
                    for x in range(0, int(width + tile_width),
                                   int(tile_width)):
                        for y in range(0, int(height + tile_height),
                                       int(tile_height)):
                            cr.save()
                            cr.translate(x, y)
                            cr.scale(tile_scale, tile_scale)
                            Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
                            cr.paint_with_alpha(brightness)
                            cr.restore()

                elif fitting == 'spanned':
                    # Spanned - stretch to fill
                    cr.save()
                    cr.scale(width / image_width, height / image_height)
                    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
                    cr.paint_with_alpha(brightness)
                    cr.restore()

        except Exception as e:
            # If there's an error, just show the background color
            pass

    def on_setting_changed(self, widget, *args):
        self.preview_area.queue_draw()

    def show_toast(self, text, success=True):
        toast = Adw.Toast.new(text)
        # if not success:
        # toast.add_css_class('error')
        self.toast_overlay.add_toast(toast)

    def apply_settings(self):
        try:
            selected_text = self.combo.get_selected_item().get_string()
            option_value = self.fitting_options[selected_text]

            color = self.color_button.get_rgba()
            color_str = f"rgb({int(color.red*255)},{int(color.green*255)},{int(color.blue*255)})"

            brightness = self.brightness_scale.get_value() / 100

            self._apply_settings_sync(option_value, color_str, brightness)
            GLib.idle_add(self.show_toast, "Settings applied successfully")

        except Exception as e:
            GLib.idle_add(self.show_toast, f"Error: {str(e)}", False)
        finally:
            GLib.idle_add(self.spinner.stop)
            GLib.idle_add(self.apply_button.set_sensitive, True)

    def _apply_settings_sync(self, option_value, color_str, brightness):
        subprocess.run([
            'gsettings', 'set', 'org.gnome.desktop.background',
            'picture-options', option_value
        ])
        subprocess.run([
            'gsettings', 'set', 'org.gnome.desktop.background',
            'primary-color', color_str
        ])
        subprocess.run([
            'gsettings', 'set', 'org.gnome.desktop.background',
            'picture-opacity',
            str(brightness)
        ])

    def on_apply_clicked(self, button):
        self.spinner.start()
        self.apply_button.set_sensitive(False)
        self.executor.submit(self.apply_settings)


class WallpaperApp(Adw.Application):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.add_action(about_action)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()

    def on_about_action(self, action, param):
        about = Adw.AboutWindow(
            transient_for=self.win,
            application_name="Wallpaper Adjuster",
            application_icon="preferences-desktop-wallpaper",
            developer_name="ren-chon (corewwwi)",
            version=VERSION,
            copyright="© 2024",
            website=f"https://github.com/{GITHUB_USER}/wallpaper-adjuster",
            issue_url=
            f"https://github.com/{GITHUB_USER}/wallpaper-adjuster/issues",
            developers=[
                f"GitHub: https://github.com/{GITHUB_USER}",
                f"Twitter: https://twitter.com/{TWITTER_USER}"
            ],
            license_type=Gtk.License.GPL_3_0)
        about.present()


def main():
    app = WallpaperApp(application_id=APP_ID)
    app.run(None)


if __name__ == "__main__":
    main()
