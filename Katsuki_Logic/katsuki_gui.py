import os, threading, tkinter as tk
from io import BytesIO
from PIL import ImageTk, Image
from tkinter import ttk, filedialog, messagebox
from .katsuki_gauntlets import LILAC, setup_lilac_styles, apply_lilac_to_root, BackgroundUnpacker, ModPacker, ModManagerLogic, log, WinMMAudioPlayer, rebuild_subcontainer_from_folder

"""
This script handles the GUI logic of Katsuki Engine, calling functions as needed from katsuki_gauntlets
"""

class ModManagerWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Katsuki Mod Manager")
        self.geometry("1150x950")
        
        apply_lilac_to_root(self)
        
        self.logic = ModManagerLogic()
        self._audio_player = WinMMAudioPlayer(log=log)
        self.current_mod_data = None
        self.music_enabled = tk.BooleanVar(value=True) # The Toggle
        self.image_index = 0
        self.tk_img = None
        self.card_widgets = {}
        self.selected_card = None
        
        self.setup_ui()
        
        self.refresh_mod_list()

    def setup_ui(self):
        """Handles GUI setup"""
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        self.gallery_frame = tk.Frame(self, bg=LILAC)
        self.gallery_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        filter_container = tk.Frame(self.gallery_frame, bg="#D191FB", bd=2, relief="ridge", padx=10, pady=10)
        filter_container.pack(side="top", fill="x", pady=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_mod_list())
        
        search_frame = tk.Frame(filter_container, bg="#D191FB")
        search_frame.pack(fill="x", pady=(0, 5))
        tk.Label(
            search_frame,
            text="Filter",
            bg="#D191FB",
            fg="#311238",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left")
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 11), bg="#E0B0FF", relief="flat")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.active_genre = tk.StringVar(value="All")
        self.active_genre.trace_add("write", lambda *args: self.refresh_mod_list())

        genre_frame = tk.Frame(filter_container, bg="#D191FB")
        genre_frame.pack(fill="x")
        
        genres = ["All", "Texture", "Audio", "Model", "Overhaul"]
        for g in genres:
            rb = tk.Radiobutton(genre_frame, text=g, variable=self.active_genre, value=g, 
                                bg=LILAC, activebackground="#D191FB", selectcolor="#D191FB", 
                                indicatoron=0, width=7, font=("Segoe UI", 8, "bold"))
            rb.pack(side="left", padx=2, fill="x", expand=True)

        self.canvas = tk.Canvas(self.gallery_frame, bg=LILAC, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.gallery_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=LILAC)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind("<Configure>", self.configure_canvas_window)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.detail_frame = tk.Frame(self, bg="#D191FB", bd=2, relief="ridge")
        self.detail_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        ctrl_frame = tk.Frame(self.detail_frame, bg="#D191FB")
        ctrl_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Checkbutton(ctrl_frame, text="Enable Mod Background Music", 
                       variable=self.music_enabled, bg="#D191FB", 
                       activebackground="#D191FB", command=self.stop_audio).pack(side="left")

        self.lbl_title = tk.Label(self.detail_frame, text="Mod Data Analysis", font=("Impact", 20), bg="#D191FB", fg="black")
        self.lbl_title.pack(pady=10)

        self.meta_row = tk.Frame(self.detail_frame, bg="#D191FB")
        self.meta_row.pack(fill="x", padx=20, pady=(0, 8))

        self.lbl_version_chip = tk.Label(
            self.meta_row, text="Version: ",
            font=("Segoe UI", 9, "bold"),
            bg="#E8D4F8", fg="#4b2354",
            padx=10, pady=4
        )
        self.lbl_version_chip.pack(side="left", padx=(0, 6))

        self.lbl_genre_chip = tk.Label(
            self.meta_row, text="Genre: ",
            font=("Segoe UI", 9, "bold"),
            bg="#E8D4F8", fg="#4b2354",
            padx=10, pady=4
        )
        self.lbl_genre_chip.pack(side="left", padx=6)

        self.lbl_mode_chip = tk.Label(
            self.meta_row, text="Mode: ",
            font=("Segoe UI", 9, "bold"),
            bg="#E8D4F8", fg="#4b2354",
            padx=10, pady=4
        )
        self.lbl_mode_chip.pack(side="left", padx=6)

        self.lbl_image_count = tk.Label(
            self.meta_row, text="Images: 0/0",
            font=("Segoe UI", 9, "bold"),
            bg="#E8D4F8", fg="#4b2354",
            padx=10, pady=4
        )
        self.lbl_image_count.pack(side="right")

        img_wrapper = tk.Frame(self.detail_frame, bg="#D191FB")
        img_wrapper.pack(pady=5, padx=20)

        self.preview_header = tk.Frame(img_wrapper, bg="#B97EEA", height=28)
        self.preview_header.pack(fill="x")
        self.preview_header.pack_propagate(False)

        self.preview_label = tk.Label(
            self.preview_header,
            text="Preview Gallery",
            font=("Segoe UI", 9, "bold"),
            bg="#B97EEA",
            fg="#240b2c"
        )
        self.preview_label.pack(side="left", padx=10)

        self.img_container = tk.Frame(img_wrapper, bg="black", width=500, height=500, bd=2, relief="sunken")
        self.img_container.pack_propagate(0)
        self.img_container.pack()
        
        self.img_label = tk.Label(self.img_container, bg="black", text="[No Mod Selected]", fg="lime")
        self.img_label.pack(fill="both", expand=True)

        nav_frame = tk.Frame(self.detail_frame, bg="#D191FB")
        nav_frame.pack(pady=5)
        ttk.Button(nav_frame, text=" < Prev Image ", command=lambda: self.cycle_image(-1)).pack(side="left", padx=10)
        ttk.Button(nav_frame, text=" Next Image > ", command=lambda: self.cycle_image(1)).pack(side="left", padx=10)

        self.btn_container = tk.Frame(self.detail_frame, bg="#D191FB")
        self.btn_container.pack(side="bottom", fill="x", padx=20, pady=12)

        self.btn_apply = tk.Button(
            self.btn_container,
            text="Enable Mod",
            command=self.apply_selected_mod,
            font=("Segoe UI", 10, "bold"),
            bg="#45C16E",
            fg="white",
            activebackground="#2FA356",
            activeforeground="white",
            relief="raised",
            bd=2,
            padx=16,
            pady=8
        )
        self.btn_apply.pack(side="left", padx=10)

        ttk.Button(self.btn_container, text="Disable Mod", command=self.disable_selected_mod).pack(side="left", padx=10)
        ttk.Button(self.btn_container, text="Disable All Mods", command=self.hard_reset_mods).pack(side="left", padx=10)

        info_container = tk.Frame(self.detail_frame, bg="#D191FB")
        info_container.pack(pady=10, fill="both", expand=True, padx=20)

        self.lbl_author = tk.Label(info_container, text="Author: ", font=("Segoe UI", 11, "bold"), bg="#D191FB", anchor="w")
        self.lbl_author.pack(fill="x")

        self.lbl_desc_header = tk.Label(
            info_container,
            text="Description",
            font=("Segoe UI", 10, "bold"),
            bg="#D191FB",
            fg="#311238",
            anchor="w"
        )
        self.lbl_desc_header.pack(fill="x", pady=(10, 2))

        self.txt_desc = tk.Text(
            info_container,
            height=8,
            bg="#EAD7F7",
            fg="#2b1630",
            font=("Segoe UI", 10),
            wrap="word",
            relief="flat",
            bd=0,
            padx=10,
            pady=10
        )
        self.txt_desc.pack(fill="both", expand=True, pady=5)
        self.txt_desc.insert("1.0", "Select a mod package to begin analysis")
        self.txt_desc.config(state="disabled")

        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

    def make_panel(self, parent, bg="#D191FB", padx=10, pady=10):
        return tk.Frame(parent, bg=bg, bd=2, relief="ridge", padx=padx, pady=pady)

    def trunc(self, text, max_len=28):
        return text if len(text) <= max_len else text[:max_len - 3] + "..."

    def configure_canvas_window(self, event):
        """Forces the inner scrollable frame to expand to the canvas width"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear_mod_selection(self):
        self.stop_audio()
        self.selected_card = None
        self.current_mod_path = None
        self.current_mod_data = None
        self.image_index = 0
        self.lbl_title.config(text="Mod Data Analysis")
        self.lbl_author.config(text="Author: ")
        self.lbl_version_chip.config(text="Version: ")
        self.lbl_genre_chip.config(text="Genre: ")
        self.lbl_mode_chip.config(text="Mode: ")
        self.lbl_image_count.config(text="Images: 0/0")
        self.txt_desc.config(state="normal")
        self.txt_desc.delete("1.0", tk.END)
        self.txt_desc.insert("1.0", "Select a mod package to begin analysis")
        self.txt_desc.config(state="disabled")
        self.img_label.config(image="", text="[No Mod Selected]", bg="black")
        self.btn_apply.config(text="Enable Mod", command=self.apply_selected_mod)

    def refresh_mod_list(self, *args):
        self.card_widgets = {}
        self.clear_mod_selection()
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not os.path.exists("Mods"):
            os.makedirs("Mods")

        applied_mods = self.logic.get_applied_mods()
        mod_files = [f for f in os.listdir("Mods") if f.endswith(".aot2mi") or f.endswith(".aot2m")]

        search_query = self.search_var.get().lower() if hasattr(self, 'search_var') else ""
        selected_genre = self.active_genre.get() if hasattr(self, 'active_genre') else "All"

        if not mod_files:
            tk.Label(self.scrollable_frame, text="No .aot2m/aot2mi packages found", bg=LILAC, fg="gray").pack(pady=20)
            return

        visible_count = 0

        for mod_file in mod_files:
            mod_path = os.path.join("Mods", mod_file)
            header = self.logic.get_mod_header(mod_path)
            
            if header:
                mod_name = self.trunc(mod_file, 28)

                genre = header['meta'].get('genre', 'Unknown') 
                
                if search_query and search_query not in mod_file.lower():
                    continue
                if selected_genre != "All" and selected_genre != genre:
                    continue
                
                status = "ACTIVE" if mod_file in applied_mods else "INACTIVE"
                bracket_color = "#32CD32" if status == "ACTIVE" else "#8A2BE2" 
                
                is_release = header.get('is_release', True) 
                rel_str = "Release" if is_release else "Debug"
                author = header['meta'].get('author', 'Unknown')
                
                subtitle = f"Auth: {author} | {rel_str} | {genre}"
                
                card = HoverCard(
                    self.scrollable_frame,
                    title=mod_name,
                    subtitle=subtitle,
                    command=lambda m=mod_path: self.on_mod_select(m),
                    color=bracket_color
                )
                card.pack(pady=6, padx=6, fill="x")
                self.card_widgets[mod_path] = card
                visible_count += 1
                
        if visible_count == 0:
            tk.Label(self.scrollable_frame, text="No mods match the current filters.", bg=LILAC, fg="#5e2f5e").pack(pady=20)

    def on_mod_select(self, mod_path):
        self.stop_audio() # Kill previous music
        if self.selected_card and self.selected_card.winfo_exists():
            self.selected_card.set_selected(False)
        else:
            self.selected_card = None
        selected = self.card_widgets.get(mod_path)
        if selected:
            selected.set_selected(True)
            self.selected_card = selected
        self.current_mod_path = mod_path
        data = self.logic.get_mod_header(mod_path)
        if not data: return

        self.current_mod_data = data
        self.image_index = 0
        
        self.lbl_title.config(text=os.path.basename(mod_path))
        self.lbl_author.config(text=f"Author: {data['meta'].get('author', 'Unknown')}")
        
        self.txt_desc.config(state="normal")
        self.txt_desc.delete("1.0", tk.END)
        self.txt_desc.insert("1.0", data['meta']['description'])
        self.txt_desc.config(state="disabled")

        version = data["meta"].get("version", "")
        genre = data["meta"].get("genre", "Unknown")
        mode = "Release" if data.get("is_release", True) else "Debug"

        self.lbl_version_chip.config(text=f"Version: {version}")
        self.lbl_genre_chip.config(text=f"Genre: {genre}")
        self.lbl_mode_chip.config(text=f"Mode: {mode}")

        img_total = len(data.get("images", []))
        self.lbl_image_count.config(text=f"Images: {1 if img_total else 0}/{img_total}")

        if data["type"] == "installer":
            self.btn_apply.config(text="Launch Installer Wizard", command=self.launch_wizard)
        else:
            self.btn_apply.config(text="Enable Mod", command=self.apply_selected_mod)

        audio = data.get("audio")
        if self.music_enabled.get() and audio:
            if len(audio) >= 12 and audio[:4] == b"RIFF" and audio[8:12] == b"WAVE":
                self._audio_player.play_loop_bytes(audio)
            else:
                log.warning("Selected mod audio is not RIFF/WAVE. First 16 bytes: %r", audio[:16])
        else:
            self._audio_player.stop()

        self.update_image_display()

    def stop_audio(self):
        """Stops any looping audio started by play_audio_loop()."""
        self._audio_player.stop()

    def destroy(self):
        self.stop_audio()
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass
        super().destroy()

    def update_image_display(self):
        if not self.current_mod_data or not self.current_mod_data.get('images'):
            self.lbl_image_count.config(text="Images: 0/0")
            self.img_label.config(image="", text="[NO VISUAL DATA]", bg=LILAC) 
            return

        try:
            images = self.current_mod_data.get('images', [])
            raw_data = images[self.image_index]
            
            img = Image.open(BytesIO(raw_data))
            img.thumbnail((500, 500)) 
            self.tk_img = ImageTk.PhotoImage(img)
            self.img_label.config(image=self.tk_img, text="", bg=LILAC) 
        except Exception as e:
            self.img_label.config(image="", text=f"IMG ERROR: {e}", bg="red")

    def cycle_image(self, delta):
        if not self.current_mod_data or not self.current_mod_data['images']:
            return
            
        total_images = len(self.current_mod_data['images'])
        self.image_index = (self.image_index + delta) % total_images
        self.lbl_image_count.config(text=f"Images: {self.image_index + 1}/{total_images}")
        self.update_image_display()

    def confirm_collision_apply(self, mod_path, keys):
        collisions, skipped_mods = self.logic.get_active_collision_report(
            keys,
            exclude_mod_name=os.path.basename(mod_path)
        )
        if not collisions and not skipped_mods:
            return True

        message = self.logic.build_collision_message(
            os.path.basename(mod_path),
            collisions,
            skipped_mods,
            len(keys)
        )
        return messagebox.askyesno("Mod Collision Detected", message)

    def apply_selected_mod(self):
        if self.current_mod_path:
            records = self.logic.iter_standard_mod_records(self.current_mod_path, include_data=False)
            keys = {record["key"] for record in records}
            if not self.confirm_collision_apply(self.current_mod_path, keys):
                return

            success, msg = self.logic.apply_mod(self.current_mod_path)
            dialog = messagebox.showinfo if success else messagebox.showerror
            dialog("Operation Result", msg)
            self.refresh_mod_list()

    def disable_selected_mod(self):
        if self.current_mod_path:
            success, msg = self.logic.disable_mod(self.current_mod_path)
            dialog = messagebox.showinfo if success else messagebox.showerror
            dialog("Operation Result", msg)
            self.refresh_mod_list()

    def hard_reset_mods(self):
        if messagebox.askyesno("System Warning", "Restoring vanilla LINKDATA.\nThis will wipe all active mods. Proceed?"):
            success, level, msg = self.logic.disable_all()
            dialog_map = {
                "info": messagebox.showinfo,
                "warning": messagebox.showwarning,
                "error": messagebox.showerror,
            }
            dialog = dialog_map.get(level, messagebox.showinfo)
            dialog("System Reset", msg)

            if success:
                self.refresh_mod_list()

    def launch_wizard(self):
        self.stop_audio()
        if self.current_mod_path:
            InstallerWizard(self, self.current_mod_path, self.logic)

class InstallerWizard(tk.Toplevel):
    def __init__(self, master, mod_path, logic):
        super().__init__(master)
        self.title("Katsuki Installer Wizard")
        self.geometry("900x700")
        apply_lilac_to_root(self)
        
        self.mod_path = mod_path
        self.logic = logic
        self.selections = {}
        self.option_details = {}
        self.group_vars = {}
        self.tk_prev = None
        
        self.setup_ui()
        self.parse_and_build()

    def setup_ui(self):
        """Handles GUI setup for Katsuki Installer"""
        self.top_frame = tk.Frame(self, bg=LILAC, pady=10)
        self.top_frame.pack(fill="x")
        self.lbl_title = tk.Label(self.top_frame, text="Configure Installation", font=("Impact", 18), bg=LILAC)
        self.lbl_title.pack()

        self.main_split = tk.Frame(self, bg=LILAC)
        self.main_split.pack(fill="both", expand=True, padx=10, pady=10)

        self.opt_scroll_frame = tk.Frame(self.main_split, bg="#D191FB", bd=2, relief="ridge")
        self.opt_scroll_frame.pack(side="left", fill="both", expand=True)
        
        self.canvas = tk.Canvas(self.opt_scroll_frame, bg="#D191FB", highlightthickness=0)
        self.scroll_y = ttk.Scrollbar(self.opt_scroll_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_cont = tk.Frame(self.canvas, bg="#D191FB")
        
        self.canvas.create_window((0, 0), window=self.scroll_cont, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll_y.set)
        
        self.scroll_y.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.preview_frame = tk.Frame(self.main_split, bg=LILAC, width=350)
        self.preview_frame.pack(side="right", fill="both", padx=(10, 0))
        
        self.prev_canvas = tk.Canvas(self.preview_frame, bg="black", width=300, height=300)
        self.prev_canvas.pack(pady=5)
        
        self.txt_info = tk.Text(self.preview_frame, height=15, width=40, font=("Segoe UI", 9), bg="white")
        self.txt_info.pack(fill="both", expand=True)

        self.footer = tk.Frame(self, bg=LILAC, pady=10)
        self.footer.pack(fill="x")
        ttk.Button(self.footer, text="Finalize & Install", command=self.run_install).pack()

    def parse_and_build(self):
        try:
            header = self.logic.get_mod_header(self.mod_path)
            if not header or header.get("type") != "installer":
                messagebox.showerror("Wizard Error", "Selected mod is not an installer (.aot2mi).")
                return

            with open(self.mod_path, "rb") as f:
                f.seek(header["payload_offset"])

                group_count = int.from_bytes(f.read(4), "little")
                log.debug("InstallerWizard: group_count=%d payload_offset=0x%X", group_count, header["payload_offset"])

                opt_global_idx = 0

                for g_idx in range(group_count):
                    g_name_len = int.from_bytes(f.read(1), "little")
                    g_name = f.read(g_name_len).decode("utf-8", errors="ignore")

                    g_logic = int.from_bytes(f.read(1), "little")

                    g_frame = tk.LabelFrame(
                        self.scroll_cont,
                        text=f" {g_name} ",
                        bg="#D191FB",
                        font=("Segoe UI", 10, "bold"),
                    )
                    g_frame.pack(fill="x", padx=5, pady=10)

                    opt_count = int.from_bytes(f.read(4), "little")
                    log.debug("InstallerWizard: group[%d] name=%r logic=%d opt_count=%d", g_idx, g_name, g_logic, opt_count)

                    if g_logic == 1:
                        var = tk.IntVar(value=-1)
                        self.group_vars[g_idx] = var
                    else:
                        self.group_vars[g_idx] = []

                    for o_idx in range(opt_count):
                        o_name_len = int.from_bytes(f.read(1), "little")
                        o_name = f.read(o_name_len).decode("utf-8", errors="ignore")

                        o_desc = self.logic.read_krle_description(f)

                        img_size = int.from_bytes(f.read(4), "little")
                        img_blob = f.read(img_size) if img_size > 0 else None

                        self.option_details[opt_global_idx] = {"desc": o_desc, "img": img_blob}

                        file_payload_count = int.from_bytes(f.read(4), "little")
                        for _ in range(file_payload_count):
                            blob_size = int.from_bytes(f.read(4), "little")
                            f.seek(blob_size, 1)

                        if g_logic == 1:
                            w = tk.Radiobutton(
                                g_frame,
                                text=o_name,
                                variable=self.group_vars[g_idx],
                                value=o_idx,
                                bg="#D191FB",
                            )
                        else:
                            var = tk.BooleanVar(value=False)
                            self.group_vars[g_idx].append((o_name, var))
                            w = tk.Checkbutton(
                                g_frame,
                                text=o_name,
                                variable=var,
                                bg="#D191FB",
                            )

                        w.pack(anchor="w")
                        w.bind("<Enter>", lambda e, idx=opt_global_idx: self.show_details(idx))
                        opt_global_idx += 1

                    if g_logic == 1 and opt_count > 0:
                        self.group_vars[g_idx].set(0)

            self.scroll_cont.update_idletasks()
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            self.scroll_cont.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

            if group_count == 0:
                messagebox.showwarning("Installer Wizard", "This installer has 0 groups. (File may be malformed or was built without groups.)")

        except Exception as e:
            log.exception("InstallerWizard.parse_and_build failed")
            messagebox.showerror("Wizard Error", f"Failed to parse installer: {e}")
            
    def show_details(self, index):
        details = self.option_details.get(index)
        if not details: return

        self.txt_info.config(state="normal")
        self.txt_info.delete("1.0", tk.END)
        self.txt_info.insert("1.0", details['desc'])
        self.txt_info.config(state="disabled")

        if details['img']:
            try:
                img = Image.open(BytesIO(details['img']))
                img = img.resize((300, 300)) # Fit to Wizard Canvas
                self.tk_prev = ImageTk.PhotoImage(img)
                self.prev_canvas.delete("all")
                self.prev_canvas.create_image(0, 0, anchor="nw", image=self.tk_prev)
            except:
                pass
        else:
            self.prev_canvas.delete("all")
            self.prev_canvas.create_text(150, 150, text="No Preview Available", fill="gray")

    def run_install(self):
        try:
            header = self.logic.get_mod_header(self.mod_path)
            if not header or header.get("type") != "installer":
                raise ValueError("Not an installer package")

            with open(self.mod_path, "rb") as f:
                f.seek(header["payload_offset"])

                group_count = int.from_bytes(f.read(4), "little")
                selected_payloads = []

                for g_idx in range(group_count):
                    g_name_len = int.from_bytes(f.read(1), "little")
                    g_name = f.read(g_name_len).decode("utf-8", errors="ignore")

                    g_logic = int.from_bytes(f.read(1), "little")
                    opt_count = int.from_bytes(f.read(4), "little")

                    for o_idx in range(opt_count):
                        o_name_len = int.from_bytes(f.read(1), "little")
                        o_name = f.read(o_name_len).decode("utf-8", errors="ignore")

                        self.logic.read_krle_description(f)

                        img_size = int.from_bytes(f.read(4), "little")
                        if img_size:
                            f.seek(img_size, 1)

                        is_selected = False
                        if g_logic == 1:
                            is_selected = (self.group_vars[g_idx].get() == o_idx)
                        else:
                            is_selected = bool(self.group_vars[g_idx][o_idx][1].get())

                        file_payload_count = int.from_bytes(f.read(4), "little")

                        if is_selected:
                            for p_idx in range(file_payload_count):
                                f_size = int.from_bytes(f.read(4), "little")
                                selected_payloads.append({
                                    "group_index": g_idx,
                                    "option_index": o_idx,
                                    "payload_index": p_idx,
                                    "file_data": f.read(f_size),
                                })
                        else:
                            for _ in range(file_payload_count):
                                f_size = int.from_bytes(f.read(4), "little")
                                f.seek(f_size, 1)

            selected_keys, invalid_count = self.logic.get_collision_keys_from_blobs(
                [payload["file_data"] for payload in selected_payloads]
            )
            if not self.master.confirm_collision_apply(self.mod_path, selected_keys):
                return

            mod_name = os.path.basename(self.mod_path)
            if mod_name in self.logic.get_applied_mods():
                success, msg = self.logic.disable_mod(self.mod_path)
                if not success:
                    raise ValueError(msg)

            files_applied = 0
            skipped_payloads = 0
            for payload in selected_payloads:
                if self.logic.inject_raw_payload(payload["file_data"]):
                    files_applied += 1
                else:
                    skipped_payloads += 1

            tracked_count, state_invalid_count = self.logic.save_installer_selection(
                mod_name,
                selected_payloads
            )
            self.logic.update_ledger(mod_name, add=True)
            extra = ""
            missing_taildata = max(invalid_count, state_invalid_count)
            if missing_taildata:
                extra = f"\nSkipped collision tracking on {missing_taildata} payload(s) without taildata."
            if skipped_payloads:
                extra += f"\nSkipped installing {skipped_payloads} payload(s) because their taildata or target container was invalid."
            elif tracked_count == 0 and files_applied == 0:
                extra = "\nNo installer payloads were selected."
            messagebox.showinfo("Success", f"Installed {files_applied} components successfully.{extra}")
            self.master.refresh_mod_list()
            self.destroy()

        except Exception as e:
            log.exception("InstallerWizard.run_install failed")
            messagebox.showerror("Installation Failed", str(e))

class ModCreatorWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Katsuki Mod Creator")
        self.geometry("1200x900") 
        
        apply_lilac_to_root(self)
        
        self.files_to_pack = []
        self.images_to_pack = []
        self.audio_to_pack = None 
        self.preview_img = None 
        
        self.arch_data = {} 
        self.current_arch_item = None
        self.arch_preview_ref = None
        self.arch_audio_file = None
        self.build_mode_var = tk.BooleanVar(value=False) # False = Debug, True = Release
        self.mod_genre = tk.StringVar(value="Texture") # Default genre

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_standard = tk.Frame(self.tabs, bg=LILAC)
        self.tabs.add(self.tab_standard, text="  Standard Payload  ")
        
        self.tab_installer = tk.Frame(self.tabs, bg=LILAC)
        self.tabs.add(self.tab_installer, text="  Installer Architect  ")
        
        self.setup_standard_ui(self.tab_standard)
        self.setup_architect_ui(self.tab_installer)

    def create_header(self, parent, text):
        lbl = tk.Label(parent, text=text, font=("Impact", 18), bg=LILAC, fg="#5e2f5e", anchor="w")
        lbl.pack(fill="x", pady=(0, 10))
        tk.Frame(parent, bg="#5e2f5e", height=2).pack(fill="x", pady=(0, 10))

    def setup_standard_ui(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.rowconfigure(0, weight=1)

        meta_frame = tk.Frame(parent, bg=LILAC, padx=10, pady=10)
        meta_frame.grid(row=0, column=0, sticky="nsew")
        self.create_header(meta_frame, "Meta Data")

        input_container = tk.Frame(meta_frame, bg="#D191FB", bd=2, relief="ridge", padx=15, pady=15)
        input_container.pack(fill="both", expand=True)

        def create_entry(p, text):
            tk.Label(p, text=text, font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x", pady=(10, 2))
            e = tk.Entry(p, font=("Consolas", 11), bg="white", relief="flat")
            e.pack(fill="x", ipady=4)
            return e

        self.ent_name = create_entry(input_container, "Mod Package Name")
        self.ent_ver = create_entry(input_container, "Version ID")
        self.ent_auth = create_entry(input_container, "Author")
        tk.Label(input_container, text="Build Mode:", font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x", pady=(10, 2))
        mode_frame = tk.Frame(input_container, bg="#D191FB")
        mode_frame.pack(fill="x")
        tk.Radiobutton(mode_frame, text="Debug", variable=self.build_mode_var, value=False, bg="#D191FB").pack(side="left")
        tk.Radiobutton(mode_frame, text="Release", variable=self.build_mode_var, value=True, bg="#D191FB").pack(side="left")

        tk.Label(input_container, text="Mod Genre:", font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x", pady=(10, 2))
        genre_frame = tk.Frame(input_container, bg="#D191FB")
        genre_frame.pack(fill="x")
        genres = ["All", "Texture", "Audio", "Model", "Overhaul"]
        for g in genres:
            tk.Radiobutton(genre_frame, text=g, variable=self.mod_genre, value=g, bg="#D191FB").pack(side="left", padx=2)

        tk.Label(input_container, text="Description:", font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x", pady=(15, 2))
        self.txt_desc = tk.Text(input_container, height=10, font=("Consolas", 10), bg="white", relief="flat")
        self.txt_desc.pack(fill="both", expand=True, pady=2)

        payload_frame = tk.Frame(parent, bg=LILAC, padx=10, pady=10)
        payload_frame.grid(row=0, column=1, sticky="nsew")
        self.create_header(payload_frame, "Payload Manifest")

        file_container = tk.Frame(payload_frame, bg="#D191FB", bd=2, relief="ridge", padx=10, pady=10)
        file_container.pack(fill="both", expand=True)

        self.file_list = tk.Listbox(file_container, bg="black", fg="#00FF00", font=("Consolas", 10), bd=0, highlightthickness=0)
        self.file_list.pack(fill="both", expand=True, pady=(0, 10))

        btn_frame_f = tk.Frame(file_container, bg="#D191FB")
        btn_frame_f.pack(fill="x")
        ttk.Button(btn_frame_f, text="[+] Add File Resources", command=self.add_files).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_frame_f, text="[-] Drop Selection", command=self.remove_file).pack(side="left", expand=True, fill="x", padx=2)

        visual_frame = tk.Frame(parent, bg=LILAC, padx=10, pady=10)
        visual_frame.grid(row=0, column=2, sticky="nsew")
        self.create_header(visual_frame, "Visual/Audio Data")

        vis_container = tk.Frame(visual_frame, bg="#D191FB", bd=2, relief="ridge", padx=10, pady=10)
        vis_container.pack(fill="both", expand=True)

        self.preview_canvas = tk.Canvas(vis_container, bg="black", width=300, height=150, highlightthickness=0)
        self.preview_canvas.pack(pady=(0, 5), anchor="center")
        self.preview_canvas.create_text(150, 75, text="No Preview", fill="gray", font=("Segoe UI", 10))

        self.img_list = tk.Listbox(vis_container, bg="black", fg="cyan", font=("Consolas", 10), bd=0, highlightthickness=0, height=5)
        self.img_list.pack(fill="x", pady=(0, 5))

        btn_frame_i = tk.Frame(vis_container, bg="#D191FB")
        btn_frame_i.pack(fill="x", pady=(0, 15))
        ttk.Button(btn_frame_i, text="[+] Images (Max 5)", command=self.add_images).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_frame_i, text="[-] Drop Img", command=self.remove_image).pack(side="left", expand=True, fill="x", padx=2)

        tk.Label(vis_container, text="Theme Audio (WAV only):", font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x")
        self.lbl_audio = tk.Label(vis_container, text="No Audio Selected", bg="black", fg="yellow", font=("Consolas", 10), relief="sunken")
        self.lbl_audio.pack(fill="x", pady=5, ipady=4)

        btn_frame_a = tk.Frame(vis_container, bg="#D191FB")
        btn_frame_a.pack(fill="x")
        ttk.Button(btn_frame_a, text="[+] Select BGM", command=self.set_audio).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_frame_a, text="[-] Clear BGM", command=self.clear_audio).pack(side="left", expand=True, fill="x", padx=2)

        footer_frame = tk.Frame(parent, bg=LILAC, height=80)
        footer_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        
        self.btn_create = tk.Button(
            footer_frame, 
            text="Create Mod Package", 
            font=("Impact", 16), 
            bg="#32CD32", fg="white", 
            activebackground="#228B22", activeforeground="white",
            relief="raised", bd=3,
            command=self.create_mod_package
        )
        self.btn_create.pack(pady=20, ipadx=50, ipady=10)

    def setup_architect_ui(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(0, weight=1)

        left_frame = tk.Frame(parent, bg=LILAC, padx=10, pady=10)
        left_frame.grid(row=0, column=0, sticky="nsew")

        meta_frame = tk.Frame(left_frame, bg="#D191FB", bd=2, relief="ridge", padx=10, pady=10)
        meta_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(meta_frame, text="Installer Name:", font=("Segoe UI", 9, "bold"), bg="#D191FB").pack(anchor="w")
        self.ent_arch_name = tk.Entry(meta_frame, font=("Consolas", 10))
        self.ent_arch_name.pack(fill="x", pady=(0, 5))
        
        tk.Label(meta_frame, text="Version ID:", font=("Segoe UI", 9, "bold"), bg="#D191FB").pack(anchor="w")
        self.ent_arch_ver = tk.Entry(meta_frame, font=("Consolas", 10))
        self.ent_arch_ver.pack(fill="x", pady=(0, 5))

        tk.Label(meta_frame, text="Author:", font=("Segoe UI", 9, "bold"), bg="#D191FB").pack(anchor="w")
        self.ent_arch_auth = tk.Entry(meta_frame, font=("Consolas", 10))
        self.ent_arch_auth.pack(fill="x", pady=(0, 5))

        tk.Label(meta_frame, text="Mod Genre:", font=("Segoe UI", 9, "bold"), bg="#D191FB").pack(anchor="w")
        genre_frame_arch = tk.Frame(meta_frame, bg="#D191FB")
        genre_frame_arch.pack(fill="x", pady=(0, 5))
        genres = ["All", "Texture", "Audio", "Model", "Overhaul"]
        for g in genres:
            tk.Radiobutton(genre_frame_arch, text=g, variable=self.mod_genre, value=g, bg="#D191FB", font=("Segoe UI", 8)).pack(side="left", padx=2)

        tk.Label(meta_frame, text="Build Mode:", font=("Segoe UI", 9, "bold"), bg="#D191FB").pack(anchor="w", pady=(5, 0))
        mode_frame_arch = tk.Frame(meta_frame, bg="#D191FB")
        mode_frame_arch.pack(fill="x", pady=(0, 5))
        tk.Radiobutton(mode_frame_arch, text="Debug", variable=self.build_mode_var, value=False, bg="#D191FB").pack(side="left")
        tk.Radiobutton(mode_frame_arch, text="Release", variable=self.build_mode_var, value=True, bg="#D191FB").pack(side="left")

        tk.Label(meta_frame, text="Installer Description:", font=("Segoe UI", 9, "bold"), bg="#D191FB").pack(anchor="w")
        self.txt_arch_desc = tk.Text(meta_frame, height=5, font=("Consolas", 9), bg="white", relief="flat")
        self.txt_arch_desc.pack(fill="x")
        
        self.create_header(left_frame, "Installer Structure")

        tree_cont = tk.Frame(left_frame, bg="#D191FB", bd=2, relief="ridge", padx=5, pady=5)
        tree_cont.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_cont, selectmode="browse")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_arch_select)

        btn_f = tk.Frame(tree_cont, bg="#D191FB")
        btn_f.pack(fill="x", pady=5)
        ttk.Button(btn_f, text="+ Group", command=self.arch_add_group).pack(side="left", fill="x", expand=True, padx=1)
        ttk.Button(btn_f, text="+ Option", command=self.arch_add_option).pack(side="left", fill="x", expand=True, padx=1)
        ttk.Button(btn_f, text="- Delete", command=self.arch_delete).pack(side="left", fill="x", expand=True, padx=1)

        audio_frame = tk.LabelFrame(left_frame, text="Installer Music", bg=LILAC, padx=5, pady=5)
        audio_frame.pack(fill="x", pady=(10, 0))
        
        self.lbl_arch_audio = tk.Label(audio_frame, text="No Audio Selected", bg="black", fg="yellow", font=("Consolas", 9), relief="sunken")
        self.lbl_arch_audio.pack(fill="x", pady=(0, 5))
        
        af_btn = tk.Frame(audio_frame, bg=LILAC)
        af_btn.pack(fill="x")
        ttk.Button(af_btn, text="Select WAV", command=self.arch_set_audio).pack(side="left", fill="x", expand=True, padx=1)
        ttk.Button(af_btn, text="Clear", command=self.arch_clear_audio).pack(side="left", fill="x", expand=True, padx=1)

        right_frame = tk.Frame(parent, bg=LILAC, padx=10, pady=10)
        right_frame.grid(row=0, column=1, sticky="nsew")
        self.create_header(right_frame, "Component Details")

        self.det_cont = tk.Frame(right_frame, bg="#D191FB", bd=2, relief="ridge", padx=15, pady=15)
        self.det_cont.pack(fill="both", expand=True)

        self.lbl_arch_ph = tk.Label(self.det_cont, text="Select an item to edit", bg="#D191FB", fg="gray", font=("Segoe UI", 12))
        self.lbl_arch_ph.pack(expand=True)

        self.frm_grp = tk.Frame(self.det_cont, bg="#D191FB")
        tk.Label(self.frm_grp, text="Group Name:", font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x")
        self.ent_grp_name = tk.Entry(self.frm_grp, font=("Consolas", 11))
        self.ent_grp_name.pack(fill="x", pady=(0, 10))
        self.ent_grp_name.bind("<KeyRelease>", self.arch_update_name)

        tk.Label(self.frm_grp, text="Selection Type:", font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x")
        self.var_grp_type = tk.StringVar(value="Single Select") # Updated default
        tk.Radiobutton(self.frm_grp, text="Single Select", variable=self.var_grp_type, value="Single Select", bg="#D191FB", command=self.arch_update_data).pack(anchor="w")
        tk.Radiobutton(self.frm_grp, text="Multi Select", variable=self.var_grp_type, value="Multi Select", bg="#D191FB", command=self.arch_update_data).pack(anchor="w")
        
        tk.Label(self.frm_grp, text="Note: Single Select forces user to pick one.\nMulti Select allows picking any/all.", 
                 bg="#D191FB", fg="#5e2f5e", justify="left").pack(anchor="w", pady=10)

        self.frm_opt = tk.Frame(self.det_cont, bg="#D191FB")
        
        tk.Label(self.frm_opt, text="Option Name:", font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x")
        self.ent_opt_name = tk.Entry(self.frm_opt, font=("Consolas", 11))
        self.ent_opt_name.pack(fill="x", pady=(0, 5))
        self.ent_opt_name.bind("<KeyRelease>", self.arch_update_name)

        tk.Label(self.frm_opt, text="Option Description:", font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x")
        self.txt_opt_desc = tk.Text(self.frm_opt, height=4, font=("Consolas", 9), bg="white", relief="flat")
        self.txt_opt_desc.pack(fill="x", pady=(0, 10))
        self.txt_opt_desc.bind("<KeyRelease>", self.arch_update_data)

        tk.Label(self.frm_opt, text="Assigned Files:", font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x")
        self.lst_opt_files = tk.Listbox(self.frm_opt, bg="black", fg="#00FF00", height=6, font=("Consolas", 9))
        self.lst_opt_files.pack(fill="x", pady=(0, 5))
        ttk.Button(self.frm_opt, text="Manage Files", command=self.arch_manage_files).pack(anchor="w", pady=(0, 10))

        tk.Label(self.frm_opt, text="Preview Image:", font=("Segoe UI", 9, "bold"), bg="#D191FB", anchor="w").pack(fill="x")
        self.lbl_opt_img = tk.Canvas(self.frm_opt, bg="black", width=300, height=150, highlightthickness=0)
        self.lbl_opt_img.pack(pady=(0, 5), anchor="w")
        self.lbl_opt_img.create_text(150, 75, text="No Image", fill="gray", font=("Segoe UI", 10))

        ttk.Button(self.frm_opt, text="Set Image", command=self.arch_set_image).pack(anchor="w")

        self.btn_arch_build = tk.Button(right_frame, text="Generate Installer (.aot2mi)", font=("Impact", 14), bg="#32CD32", fg="white", command=self.create_installer_package)
        self.btn_arch_build.pack(side="bottom", fill="x", pady=10)

    def add_files(self):
        files = filedialog.askopenfilenames(title="Select Game Files")
        for f in files:
            if f not in self.files_to_pack:
                self.files_to_pack.append(f)
                self.file_list.insert(tk.END, os.path.basename(f))

    def remove_file(self):
        sel = self.file_list.curselection()
        if sel:
            idx = sel[0]
            self.file_list.delete(idx)
            del self.files_to_pack[idx]

    def add_images(self):
        if len(self.images_to_pack) >= 5:
            messagebox.showwarning("Limit Reached", "Max 5 images allowed.")
            return
        images = filedialog.askopenfilenames(title="Select Preview Images", filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        for img_path in images:
            if len(self.images_to_pack) >= 5: break
            if img_path not in self.images_to_pack:
                self.images_to_pack.append(img_path)
                self.img_list.insert(tk.END, os.path.basename(img_path))
        if self.images_to_pack: self.update_preview(self.images_to_pack[-1])

    def remove_image(self):
        sel = self.img_list.curselection()
        if sel:
            idx = sel[0]
            self.img_list.delete(idx)
            del self.images_to_pack[idx]
            
            if self.images_to_pack: 
                self.update_preview(self.images_to_pack[-1])
            else: 
                self.preview_canvas.delete("all")
                self.preview_canvas.create_text(150, 75, text="No Preview", fill="gray", font=("Segoe UI", 10))

    def update_preview(self, img_path):
        try:
            img = Image.open(img_path)
            img = img.resize((300, 150))
            self.preview_img = ImageTk.PhotoImage(img)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor="nw", image=self.preview_img)
        except Exception: pass

    def set_audio(self):
        wav = filedialog.askopenfilename(title="Select Theme Song", filetypes=[("WAV Audio", "*.wav")])
        if wav:
            if os.path.getsize(wav) > 10 * 1024 * 1024:
                if not messagebox.askyesno("Large File", "File > 10MB. Continue?"): return
            self.audio_to_pack = wav
            self.lbl_audio.config(text=os.path.basename(wav), fg="#00FF00")

    def clear_audio(self):
        self.audio_to_pack = None
        self.lbl_audio.config(text="No Audio Selected", fg="yellow")

    def create_mod_package(self):
        name = self.ent_name.get().strip()
        ver = self.ent_ver.get().strip()
        auth = self.ent_auth.get().strip()
        desc = self.txt_desc.get("1.0", tk.END).strip()
        is_release = self.build_mode_var.get()
        genre = self.mod_genre.get()

        if not name or not auth or not self.files_to_pack:
            messagebox.showwarning("Incomplete", "Mod Name, Author, and Files required.")
            return

        save_path = filedialog.asksaveasfilename(defaultextension=".aot2m", filetypes=[("AOT2 Mod", "*.aot2m")], initialfile=f"{name}.aot2m")
        if save_path:
            packer = ModPacker()
            success, msg = packer.create_package(
                save_path, name, ver, auth, desc, 
                self.files_to_pack, self.images_to_pack, self.audio_to_pack, 
                is_release=is_release, genre=genre
            )
            if success:
                messagebox.showinfo("Success", f"Mod Created.\n{msg}")
                self.destroy()
            else:
                messagebox.showerror("Error", msg)

    def arch_add_group(self):
        item_id = self.tree.insert("", "end", text="New Group", open=True)
        self.arch_data[item_id] = {"type": "group", "name": "New Group", "sel_type": "Single Select"} # Updated
        self.tree.selection_set(item_id)

    def arch_add_option(self):
        sel = self.tree.selection()
        if not sel:
            return

        parent_id = sel[0]
        if self.arch_data[parent_id]["type"] != "group":
            parent_id = self.tree.parent(parent_id)
            if not parent_id:
                return

        existing = self.tree.get_children(parent_id)
        n = len(existing) + 1
        opt_name = f"New Option {n}"

        item_id = self.tree.insert(parent_id, "end", text=opt_name)

        self.arch_data[item_id] = {
            "type": "option",
            "name": opt_name,
            "files": [],
            "image": None,
            "desc": "",
        }

        self.tree.selection_set(item_id)
        self.tree.item(parent_id, open=True)

    def arch_delete(self):
        sel = self.tree.selection()
        for item in sel:
            self.tree.delete(item)
            if item in self.arch_data: del self.arch_data[item]
        self.on_arch_select(None)

    def on_arch_select(self, event):
        self.lbl_arch_ph.pack_forget()
        self.frm_grp.pack_forget()
        self.frm_opt.pack_forget()

        sel = self.tree.selection()
        if not sel:
            self.lbl_arch_ph.pack(expand=True)
            return

        item_id = sel[0]
        self.current_arch_item = item_id
        data = self.arch_data.get(item_id)

        if data["type"] == "group":
            self.frm_grp.pack(fill="both", expand=True)
            self.ent_grp_name.delete(0, tk.END)
            self.ent_grp_name.insert(0, data["name"])
            self.var_grp_type.set(data["sel_type"])
        elif data["type"] == "option":
            self.frm_opt.pack(fill="both", expand=True)
            self.ent_opt_name.delete(0, tk.END)
            self.ent_opt_name.insert(0, data["name"])
            
            self.txt_opt_desc.delete("1.0", tk.END)
            self.txt_opt_desc.insert("1.0", data.get("desc", ""))
            
            self.lst_opt_files.delete(0, tk.END)
            for f in data["files"]: 
                self.lst_opt_files.insert(tk.END, os.path.basename(f))
            
            img = data["image"]
            if img: 
                self.update_arch_preview(img)
            else: 
                self.lbl_opt_img.delete("all")
                self.lbl_opt_img.create_text(150, 75, text="No Image", fill="gray", font=("Segoe UI", 10))

    def arch_update_name(self, event=None):
        if not self.current_arch_item: return
        data = self.arch_data[self.current_arch_item]
        new_name = self.ent_grp_name.get() if data["type"] == "group" else self.ent_opt_name.get()
        data["name"] = new_name
        self.tree.item(self.current_arch_item, text=new_name)

    def arch_update_data(self, event=None):
        if not self.current_arch_item: return
        data = self.arch_data[self.current_arch_item]
        if data["type"] == "group":
            data["sel_type"] = self.var_grp_type.get()
        elif data["type"] == "option":
            data["desc"] = self.txt_opt_desc.get("1.0", tk.END).strip()

    def arch_manage_files(self):
        if not self.current_arch_item: return
        data = self.arch_data[self.current_arch_item]
        files = filedialog.askopenfilenames(title="Select Option Files")
        if files:
            data["files"] = list(files)
            self.lst_opt_files.delete(0, tk.END)
            for f in files: self.lst_opt_files.insert(tk.END, os.path.basename(f))

    def arch_set_image(self):
        if not self.current_arch_item: return
        data = self.arch_data[self.current_arch_item]
        img = filedialog.askopenfilename(title="Option Image", filetypes=[("Images", "*.png;*.jpg")])
        if img:
            data["image"] = img
            self.update_arch_preview(img)

    def arch_set_audio(self):
        wav = filedialog.askopenfilename(title="Select Installer Theme", filetypes=[("WAV Audio", "*.wav")])
        if wav:
            if os.path.getsize(wav) > 10 * 1024 * 1024:
                if not messagebox.askyesno("Large File", "File > 10MB. Continue?"): return
            self.arch_audio_file = wav
            self.lbl_arch_audio.config(text=os.path.basename(wav), fg="#00FF00")

    def arch_clear_audio(self):
        self.arch_audio_file = None
        self.lbl_arch_audio.config(text="No Audio Selected", fg="yellow")

    def update_arch_preview(self, path):
        try:
            img = Image.open(path)
            img = img.resize((300, 150))
            self.arch_preview_ref = ImageTk.PhotoImage(img)
            self.lbl_opt_img.delete("all")
            self.lbl_opt_img.create_image(0, 0, anchor="nw", image=self.arch_preview_ref)
        except: pass

    def create_installer_package(self):
        name = self.ent_arch_name.get().strip()
        version = self.ent_arch_ver.get().strip()
        author = self.ent_arch_auth.get().strip()
        desc = self.txt_arch_desc.get("1.0", tk.END).strip()
        is_release = self.build_mode_var.get()
        genre = self.mod_genre.get()
        
        if not name:
            messagebox.showwarning("Required", "Please enter an Installer Name.")
            return

        groups = self.tree.get_children("")
        if not groups:
            messagebox.showwarning("Structure Empty", "Add at least one Group and Option.")
            return

        save_path = filedialog.asksaveasfilename(defaultextension=".aot2mi", filetypes=[("AOT2 Installer", "*.aot2mi")], initialfile=f"{name}.aot2mi")
        if save_path:
            packer = ModPacker()
            success, msg = packer.create_installer_package(
                save_path, name, version, author, desc,
                self.arch_audio_file, self.arch_data, self.tree,
                is_release=is_release, genre=genre
            )
            if success:
                messagebox.showinfo("Success", msg)
                self.destroy()
            else:
                messagebox.showerror("Error", msg)
        
class CoreTools():
    def __init__(self, root):
        self.root = root
        self.root.title("Katsuki Engine, Attack On Titan 2 Toolkit")
        self.mod_creator_window = None
        self.mod_manager_window = None
        self.root.geometry("800x900")
        self.root.resizable(False, False)

        setup_lilac_styles(self.root)
        apply_lilac_to_root(self.root)

        self.progress = None
        self.active_task = None
        
        self.gui_setup()
        self.init_progress()

    def ui_notify(self, kind, title, message):
        """Thread-safe, can be called from worker threads"""
        def _do():
            if kind == "warning":
                messagebox.showwarning(title, message)
            elif kind == "error":
                messagebox.showerror(title, message)
            else:
                messagebox.showinfo(title, message)

        self.root.after(0, _do)

    def gui_setup(self):
        """Main GUI setup, the hub so to speak"""
        self.bg = ttk.Frame(self.root, style="Lilac.TFrame")
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)

        header_frame = tk.Frame(self.bg, bg=LILAC)
        header_frame.pack(pady=(50, 40), fill="x")
        
        ttk.Label(
            header_frame, 
            text="Katsuki Engine", 
            font=("Impact", 36), 
            style="Lilac.TLabel"
        ).pack()
        
        ttk.Label(
            header_frame, 
            text="AOT2 Modding Toolkit", 
            font=("Segoe UI", 10, "bold"), 
            foreground="#5e2f5e", 
            style="Lilac.TLabel"
        ).pack()

        card_container = tk.Frame(self.bg, bg=LILAC)
        card_container.pack(expand=False, side="top", anchor="n")

        self.btn_creator = HoverCard(
            card_container, 
            title="Mod Creator", 
            subtitle="Pack files into .aot2m/.aot2mi mods", 
            command=self.open_mod_creator_window
        )
        self.btn_creator.pack(pady=12)

        self.btn_manager = HoverCard(
            card_container, 
            title="Mod Manager", 
            subtitle="Apply, toggle, or disable active mods", 
            command=self.open_mod_manager_window
        )
        self.btn_manager.pack(pady=12)

        self.btn_unpack = HoverCard(
            card_container, 
            title="Unpack Bins", 
            subtitle="Extract BIN files", 
            command=self.start_unpacking
        )
        self.btn_unpack.pack(pady=12)

        self.btn_rebuild_sub = HoverCard(
            card_container,
            title="Rebuild Subcontainer",
            subtitle="Pack an extracted subfolder back into one file",
            command=self.start_subcontainer_rebuild
        )
        self.btn_rebuild_sub.pack(pady=12)

        self.status_label = ttk.Label(
            self.bg,
            text="System Ready",
            style="Lilac.TLabel",
            font=("Segoe UI", 9, "bold")
        )
        self.status_label.pack(side="bottom", pady=(0, 80))

    def open_mod_manager_window(self):
        """
        Singleton Pattern, only opens if not already open
        """
        if self.mod_manager_window is None or not self.mod_manager_window.winfo_exists():
            self.mod_manager_window = ModManagerWindow(self.root)
        else:
            self.mod_manager_window.lift() # Bring to front
            self.mod_manager_window.focus_force()

    def open_mod_creator_window(self):
        """
        Singleton Pattern, only opens if not already open
        """
        if self.mod_creator_window is None or not self.mod_creator_window.winfo_exists():
            self.mod_creator_window = ModCreatorWindow(self.root)
        else:
            self.mod_creator_window.lift() # Bring to front
            self.mod_creator_window.focus_force()

    def init_progress(self):
        """
        Create a progress bar/label at the bottom of the window
        """
        self.progress = {}
        self.progress["var"] = tk.StringVar(value="Idle")

        bar = ttk.Progressbar(self.bg, mode="determinate", length=600)
        bar.place(x=100, y=750)
        self.progress["bar"] = bar

        prog_label = ttk.Label(
            self.bg,
            textvariable=self.progress["var"],
            style="Lilac.TLabel"
        )
        prog_label.place(x=100, y=780)

    def set_status(self, text, color=None):
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda: self.set_status(text, color))
            return
        if color is None:
            self.status_label.config(text=text)
        else:
            self.status_label.config(text=text, foreground=color)

    def set_progress(self, done, total, note=None):
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda: self.set_progress(done, total, note))
            return
        if self.progress is None:
            return

        bar = self.progress["bar"]
        var = self.progress["var"]

        total = max(1, int(total))
        done = min(int(done), total)

        if int(bar["maximum"] or 0) != total:
            bar.configure(maximum=total)

        bar["value"] = done

        if note is None:
            pct = (done * 100) // total
            var.set(f"Working {done}/{total} ({pct}%)")
        else:
            var.set(note)

        self.root.update_idletasks()

    def start_unpacking(self):
        """Triggered by a button click"""
        if self.active_task:
            self.set_status(f"{self.active_task} already running", "orange")
            return

        self.active_task = "Unpack"
        thread = threading.Thread(target=self.run_unpack_task, daemon=True)
        thread.start()

    def start_subcontainer_rebuild(self):
        if self.active_task:
            self.set_status(f"{self.active_task} already running", "orange")
            return

        self.active_task = "Subcontainer rebuild"
        folder_path = filedialog.askdirectory(title="Select Extracted Subcontainer Folder")
        if not folder_path:
            self.active_task = None
            return

        original_path = filedialog.askopenfilename(
            title="Select Original Unpacked Subcontainer File",
            filetypes=[("All Files", "*.*")]
        )
        if not original_path:
            self.active_task = None
            return

        thread = threading.Thread(
            target=self.run_subcontainer_rebuild_task,
            args=(folder_path, original_path),
            daemon=True
        )
        thread.start()

    def run_unpack_task(self):
        """The actual work loop running in the thread, containers will be unpacked"""
        unpacker = BackgroundUnpacker(
            progress_callback=self.set_progress,
            ui_notify=self.ui_notify
        )
        
        try:
            unpack_jobs = [
                ("LINKDATA_A.BIN", "LINK_A", 0),
                ("LINKDATA_B.BIN", "LINK_B", 1),
                ("LINKDATA_C.BIN", "LINK_C", 2),
                ("LINKDATA_D.BIN", "LINK_D", 3),
                ("LINKDATA_DEBUG.BIN", "LINK_DEBUG", 4),
                ("LINKDATA_DLC.BIN", "LINK_DLC", 5),
                ("LINKDATA_PLATFORM_DX11.BIN", "LINK_PLATFORM_DX11", 6),
                ("LINKDATA_PLATFORM_EDEN_DX11.BIN", "LINK_PLATFORM_EDEN", 7),
                ("REGION/LINKDATA_REGION_JP.BIN", "REGION_JP", 8),
                ("REGION/LINKDATA_REGION_AS.BIN", "REGION_AS", 9),
                ("REGION/LINKDATA_REGION_EDEN_AS.BIN", "REGION_EDEN_AS", 10),
                ("REGION/LINKDATA_REGION_EDEN_EU.BIN", "REGION_EDEN_EU", 11),
                ("REGION/LINKDATA_REGION_EDEN_JP.BIN", "REGION_EDEN_JP", 12),
                ("REGION/LINKDATA_REGION_EU.BIN", "REGION_EU", 13),
                ("EX/LINKDATA_EX_MASTER.BIN", "LINK_EX", 14),
                ("PATCH/LINKDATA_PATCH_000.BIN", "LINK_PATCH", 15),
                ("PATCH/LINKDATA_PATCH_EDEN_000.BIN", "LINK_PATCH_EDEN", 16),
            ]

            for bin_path, folder_name, container_id in unpack_jobs:
                self.set_status(f"Processing {os.path.basename(bin_path)}", "blue")
                unpacker.unpack_resource(bin_path, folder_name, container_id)
            
            self.set_status("Unpacking Complete.", "green")
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda err=err: messagebox.showerror("Error", f"Unpacking failed: {err}"))
        finally:
            self.root.after(0, lambda: setattr(self, "active_task", None))

    def run_subcontainer_rebuild_task(self, folder_path, original_path):
        try:
            self.set_progress(0, 1, "Rebuilding subcontainer")
            self.set_status("Rebuilding subcontainer", "blue")
            output_path, msg = rebuild_subcontainer_from_folder(folder_path, original_path)
            self.set_progress(1, 1, "Subcontainer rebuild complete.")
            self.set_status("Subcontainer rebuild complete.", "green")
            self.ui_notify("info", "Subcontainer Rebuilt", f"{msg}\n\nSaved to:\n{output_path}")
        except Exception as e:
            log.exception("Subcontainer rebuild failed")
            self.set_progress(0, 1, "Subcontainer rebuild failed.")
            self.set_status("Subcontainer rebuild failed.", "red")
            self.ui_notify("error", "Rebuild Error", str(e))
        finally:
            self.root.after(0, lambda: setattr(self, "active_task", None))

class HoverCard(tk.Canvas):
    def __init__(self, master, title, subtitle, command, color="#E0B0FF", width=320, height=108, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            bg=LILAC,
            highlightthickness=0,
            bd=0,
            **kwargs
        )
        self.command = command
        self.color = color
        self.default_bg = "#C9A9C9"
        self.hover_bg = "#D9B8F2"
        self.selected_bg = "#E5C7FF"
        self.is_selected = False

        self.rect = self.create_rectangle(
            6, 6, width - 6, height - 6,
            fill=self.default_bg,
            outline=color,
            width=2
        )

        self.accent = self.create_rectangle(
            10, 10, 16, height - 10,
            fill=color,
            outline=color
        )

        self.title_text = self.create_text(
            28, 34,
            text=title,
            font=("Segoe UI", 14, "bold"),
            anchor="w",
            fill="#1f1024"
        )

        self.sub_text = self.create_text(
            28, 63,
            text=subtitle,
            font=("Segoe UI", 9),
            anchor="w",
            fill="#5e2f5e",
            width=width - 50
        )

        for tag in (self.rect, self.accent, self.title_text, self.sub_text):
            self.tag_bind(tag, "<Enter>", self.on_enter)
            self.tag_bind(tag, "<Leave>", self.on_leave)
            self.tag_bind(tag, "<Button-1>", self.on_click)

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def on_click(self, event=None):
        self.command()
        return "break"

    def set_selected(self, selected: bool):
        if not self.winfo_exists():
            return
        self.is_selected = selected
        fill = self.selected_bg if selected else self.default_bg
        self.itemconfig(self.rect, fill=fill, width=3 if selected else 2)

    def on_enter(self, event=None):
        if not self.is_selected:
            self.itemconfig(self.rect, fill=self.hover_bg)
        self.config(cursor="hand2")

    def on_leave(self, event=None):
        if not self.is_selected:
            self.itemconfig(self.rect, fill=self.default_bg)
        self.config(cursor="")
