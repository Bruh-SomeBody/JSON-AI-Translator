import json, os, time, threading, ctypes, math
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from google import genai
from google.genai import types

try:
    import sv_ttk, pywinstyles
    HAS_MODERN_UI = True
except ImportError:
    HAS_MODERN_UI = False

# === COMPACT LANGUAGE DATABASE ===
LANG_DATA = {
    "Europe & North America": {"en": "English", "ru": "Russian", "uk": "Ukrainian",
                               "be": "Belarusian", "ro": "Romanian",
                               "bg": "Bulgarian", "cs": "Czech", "pl": "Polish",
                               "sk": "Slovak", "sl": "Slovenian", "hr": "Croatian",
                               "sr": "Serbian", "bs": "Bosnian",
                               "mk": "Macedonian", "sq": "Albanian", "el": "Greek",
                               "hu": "Hungarian", "et": "Estonian", "lv": "Latvian",
                               "lt": "Lithuanian", "fi": "Finnish", "sv": "Swedish",
                               "no": "Norwegian", "da": "Danish", "de": "German",
                               "nl": "Dutch", "fr": "French",
                               "it": "Italian", "es": "Spanish",
                               "pt": "Portuguese", "ga": "Irish",
                               "mt": "Maltese", "is": "Icelandic", "cy": "Welsh",
                               "gd": "Scots Gaelic", "eo": "Esperanto", "la": "Latin"},
    "CIS & Caucasus": {"kk": "Kazakh", "uz": "Uzbek", "ky": "Kyrgyz",
                       "tg": "Tajik", "tk": "Turkmen", "az": "Azerbaijani",
                       "hy": "Armenian", "ka": "Georgian"},
    "Asia": {"zh-CN": "Chinese (Simp.)", "zh-TW": "Chinese (Trad.)",
             "ja": "Japanese", "ko": "Korean", "hi": "Hindi", "ar": "Arabic",
             "tr": "Turkish", "fa": "Persian", "he": "Hebrew", "th": "Thai",
             "vi": "Vietnamese", "id": "Indonesian", "ms": "Malay",
             "bn": "Bengali", "ur": "Urdu", "my": "Burmese",
             "km": "Khmer", "lo": "Lao", "ne": "Nepali",
             "si": "Sinhala", "ta": "Tamil", "te": "Telugu",
             "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi",
             "pa": "Punjabi", "gu": "Gujarati", "or": "Odia",
             "ku": "Kurdish", "ps": "Pashto", "sd": "Sindhi", "ug": "Uyghur"},
    "Africa": {"af": "Afrikaans", "am": "Amharic", "ig": "Igbo", "ha": "Hausa",
               "sn": "Shona", "so": "Somali", "sw": "Swahili", "xh": "Xhosa",
               "yo": "Yoruba", "zu": "Zulu", "ny": "Chichewa",
               "mg": "Malagasy", "rw": "Kinyarwanda", "st": "Sesotho"},
    "Americas & Oceania": {"ht": "Haitian Creole", "haw": "Hawaiian",
                           "sm": "Samoan", "mi": "Maori", "ceb": "Cebuano",
                           "jw": "Javanese", "su": "Sundanese", "tl": "Tagalog"}
}
FLAT_LANGS = {c: n for r in LANG_DATA.values() for c, n in r.items()}
ALL_LANG_CODES = list(FLAT_LANGS.keys())
POP_ORDER = ["en", "zh-CN", "hi", "es", "fr", "ar", "bn", "ru", "pt", "ur", "id", "de", "ja", "mr", "te", "tr", "ta",
             "vi", "ko", "fa", "ha", "sw", "jw", "it", "pa", "gu", "th", "am", "kn", "or", "my", "su", "uk", "ig", "uz",
             "sd", "ro", "tl", "nl", "km", "ps", "zh-TW", "pl", "rw", "ku", "ny", "mg", "sn", "zu", "xh", "af", "cs",
             "el", "sv", "bg", "hu", "sr", "be", "kk", "az", "hy", "ka", "sk", "fi", "da", "no", "hr", "sl", "lt", "lv",
             "et", "mk", "bs", "sq", "mt", "is", "cy", "gd", "eo", "la", "ht", "haw", "sm", "mi", "ceb"]
PRESET_MAIN = ["ru", "en", "uk", "es", "pt", "de", "ko", "fr", "zh-CN", "zh-TW", "ja", "pl", "hi", "ar", "tl", "da"]

CONFIG_FILE = "settings.json"
DEF_PROMPT = """You are an expert IT/Software localization translator.
Translate the values of the following JSON into the language code: '{lang}'.

CRITICAL RULES:
1. Keep the JSON keys EXACTLY the same.
2. Return ONLY a single valid JSON object. No markdown formatting.
3. PRESERVE ALL FORMATTING: Maintain all newline characters (\\n), spaces, etc.
4. CONTEXT: This is a Windows tweaking software. Maintain technical accuracy. 
Do not translate IT terms like 'bloatware', 'UWP', 'Explorer' unless there is a universally accepted translation.

Original JSON:
{source_text}"""


def center_win(win, w, h):
    win.geometry(f"{w}x{h}+{int((win.winfo_screenwidth() - w) / 2)}+{int((win.winfo_screenheight() - h) / 2)}")


def apply_sys_theme(window, theme_name):
    if not HAS_MODERN_UI: return
    try:
        window.update_idletasks()
        pywinstyles.apply_style(window, "mica")
        hwnd, val = int(window.wm_frame(), 16), ctypes.c_int(1 if theme_name == "dark" else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), 4)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), 4)
    except:
        pass


class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.root.title("JSON AI Translator PRO")
        self.root.minsize(650, 750)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.master_frame = ttk.Frame(self.root)
        self.master_frame.pack(fill="both", expand=True)

        self.style = ttk.Style(self.root)
        if "clam" in self.style.theme_names(): self.style.theme_use("clam")
        self.style.configure("Green.Horizontal.TProgressbar", background="#06B025")
        self.style.configure("Yellow.Horizontal.TProgressbar", background="gold")

        self.client = None
        self.is_running, self.is_paused, self.is_stopped = False, False, False
        self.custom_lang_vars = {code: tk.BooleanVar() for code in ALL_LANG_CODES}
        for var in self.custom_lang_vars.values(): var.trace_add("write", self.update_lang_count)

        self.saved_api_keys, self.input_file, self.output_dir = [], "", ""
        self.lang_mode_val, self.current_theme, self.custom_prompt, self.threads_val = 1, "dark", DEF_PROMPT, 3

        self.load_settings()
        if HAS_MODERN_UI: sv_ttk.set_theme(self.current_theme)

        self.setup_ui()
        self.update_colors()
        center_win(self.root, 720, 800)

        if HAS_MODERN_UI:
            self.root.update()
            apply_sys_theme(self.root, self.current_theme)
        self.root.deiconify()

        if self.saved_api_keys:
            threading.Thread(target=self._load_models_task, args=(self.saved_api_keys[0],), daemon=True).start()

    def on_closing(self):
        if self.is_running and not messagebox.askyesno("Exit", "Translation in progress. Are you sure you want to exit?"): return
        self.is_stopped = True
        self.root.destroy()

    def toggle_theme(self):
        if not HAS_MODERN_UI: return
        self.root.withdraw()
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        sv_ttk.set_theme(self.current_theme)
        apply_sys_theme(self.root, self.current_theme)
        self.update_colors()
        self.save_settings()
        self.root.update_idletasks()
        self.root.deiconify()

    def update_colors(self):
        if not HAS_MODERN_UI: return
        bg_col, fg_col = ("#1e1e1e", "#ffffff") if self.current_theme == "dark" else ("#f3f3f3", "#000000")
        self.log_text.config(bg=bg_col, fg=fg_col, insertbackground=fg_col)
        if hasattr(self, 'prompt_text') and self.prompt_text.winfo_exists():
            self.prompt_text.config(bg=bg_col, fg=fg_col, insertbackground=fg_col)

    def update_lang_count(self, *args):
        if hasattr(self, 'lbl_count') and self.lbl_count.winfo_exists():
            self.lbl_count.config(text=f"Selected: {sum(1 for v in self.custom_lang_vars.values() if v.get())}")

    def load_settings(self):
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.saved_api_keys, self.input_file, self.output_dir = d.get("api_keys", []), d.get("input_file", ""), d.get("output_dir", "")
            self.lang_mode_val, self.current_theme = d.get("lang_mode", 1), d.get("theme", "dark")
            self.custom_prompt, self.threads_val = d.get("custom_prompt", DEF_PROMPT), d.get("threads", 3)
            for code in d.get("custom_langs", []):
                if code in self.custom_lang_vars: self.custom_lang_vars[code].set(True)
        except:
            pass

    def save_settings(self):
        token = self.token_var.get().strip()
        if token:
            if token in self.saved_api_keys: self.saved_api_keys.remove(token)
            self.saved_api_keys.insert(0, token)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"api_keys": self.saved_api_keys[:5], "input_file": self.input_file, "output_dir": self.output_dir,
                     "lang_mode": self.lang_mode.get(),
                     "custom_langs": [c for c, v in self.custom_lang_vars.items() if v.get()],
                     "theme": self.current_theme, "custom_prompt": self.custom_prompt,
                     "threads": self.threads_var.get()}, f, indent=4)
        except:
            pass

    def setup_ui(self):
        f_api = ttk.LabelFrame(self.master_frame, text="API Connection", padding=15)
        f_api.pack(fill="x", padx=15, pady=5)
        f_api.columnconfigure(0, weight=1)

        ttk.Label(f_api, text="Gemini API Key:").grid(row=0, column=0, sticky="w", columnspan=3)
        self.token_var = tk.StringVar(value=self.saved_api_keys[0] if self.saved_api_keys else "")
        self.token_combo = ttk.Combobox(f_api, show="*", textvariable=self.token_var, values=self.saved_api_keys)
        self.token_combo.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=5)

        ttk.Button(f_api, text="Paste", width=12,
                   command=lambda: self.token_var.set(self.root.clipboard_get()[:60])).grid(row=1, column=1, padx=(0, 5), pady=5)
        self.btn_load = ttk.Button(f_api, text="Refresh List",
                                   command=lambda: threading.Thread(target=self._load_models_task,
                                                                    args=(self.token_var.get().strip(),),
                                                                    daemon=True).start())
        self.btn_load.grid(row=1, column=2, pady=5)

        ttk.Label(f_api, text="Select Model:").grid(row=2, column=0, sticky="w", columnspan=3)
        self.model_combo = ttk.Combobox(f_api, state="readonly")
        self.model_combo.set("Waiting...")
        self.model_combo.grid(row=3, column=0, columnspan=3, sticky="ew")

        f_paths = ttk.LabelFrame(self.master_frame, text="Files (Saved automatically)", padding=15)
        f_paths.pack(fill="x", padx=15, pady=5)
        ttk.Button(f_paths, text="Select Source JSON", command=self.select_file, width=28).grid(row=0, column=0, pady=2)
        self.lbl_file = ttk.Label(f_paths, text=os.path.basename(self.input_file) or "No file selected")
        self.lbl_file.grid(row=0, column=1, padx=15, sticky="w")
        ttk.Button(f_paths, text="Select Output Folder", command=self.select_dir, width=28).grid(row=1, column=0, pady=2)
        self.lbl_dir = ttk.Label(f_paths, text=self.output_dir or "No folder selected")
        self.lbl_dir.grid(row=1, column=1, padx=15, sticky="w")

        f_langs = ttk.LabelFrame(self.master_frame, text="Translation Mode & Settings", padding=15)
        f_langs.pack(fill="x", padx=15, pady=5)
        self.lang_mode = tk.IntVar(value=self.lang_mode_val)
        ttk.Radiobutton(f_langs, text="Main languages (16 popular)", variable=self.lang_mode, value=1).pack(anchor="w")
        ttk.Radiobutton(f_langs, text="All available languages (~100)", variable=self.lang_mode, value=2).pack(anchor="w")

        f_cust = ttk.Frame(f_langs)
        f_cust.pack(anchor="w", fill="x", pady=2)
        ttk.Radiobutton(f_cust, text="Manual selection", variable=self.lang_mode, value=3).pack(side="left")
        ttk.Button(f_cust, text="Open language list", command=self.open_custom_lang_window).pack(side="left", padx=20)
        ttk.Separator(f_langs, orient="horizontal").pack(fill="x", pady=8)

        f_bot = ttk.Frame(f_langs)
        f_bot.pack(fill="x")
        f_bot_l = ttk.Frame(f_bot)
        f_bot_l.pack(side="left")
        self.skip_existing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(f_bot_l, text="Skip existing", variable=self.skip_existing_var).pack(side="left")
        ttk.Label(f_bot_l, text=" | Threads:").pack(side="left", padx=(5, 2))
        self.threads_var = tk.IntVar(value=self.threads_val)
        ttk.Spinbox(f_bot_l, from_=1, to=15, textvariable=self.threads_var, width=3).pack(side="left")

        f_bot_r = ttk.Frame(f_bot)
        f_bot_r.pack(side="right")
        ttk.Button(f_bot_r, text="📝 Prompt", command=self.open_prompt_editor).pack(side="left", padx=5)
        if HAS_MODERN_UI: ttk.Button(f_bot_r, text="🌗 Theme", command=self.toggle_theme).pack(side="left")

        f_run = ttk.Frame(self.master_frame, padding=15)
        f_run.pack(fill="both", expand=True)
        f_btns = ttk.Frame(f_run)
        f_btns.pack(fill="x", pady=(0, 10))
        for i in range(3): f_btns.columnconfigure(i, weight=1)

        self.btn_start = ttk.Button(f_btns, text="▶ START TRANSLATION", command=self.start_translation, style="Accent.TButton")
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=2)
        self.btn_pause = ttk.Button(f_btns, text="⏸ PAUSE", command=self.toggle_pause, state="disabled")
        self.btn_pause.grid(row=0, column=1, sticky="ew", padx=2)
        self.btn_stop = ttk.Button(f_btns, text="⏹ STOP", command=self.stop_translation, state="disabled")
        self.btn_stop.grid(row=0, column=2, sticky="ew", padx=2)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(f_run, variable=self.progress_var, maximum=100, style="Green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=5)
        self.lbl_progress = ttk.Label(f_run, text="Waiting to start...", font=("Segoe UI", 10, "bold"))
        self.lbl_progress.pack(pady=2)

        self.log_text = tk.Text(f_run, height=8, state="disabled", wrap=tk.WORD, font=("Consolas", 10), relief="flat", borderwidth=1)
        self.log_text.pack(fill="both", expand=True)

    def log(self, msg):
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")

        self.root.after(0, _append)

    def select_file(self):
        if p := filedialog.askopenfilename(filetypes=[("JSON", "*.json")]):
            self.input_file = p
            self.lbl_file.config(text=os.path.basename(p))
            self.save_settings()

    def select_dir(self):
        if p := filedialog.askdirectory():
            self.output_dir = p
            self.lbl_dir.config(text=p)
            self.save_settings()

    def interruptible_sleep(self, seconds):
        for _ in range(int(seconds * 10)):
            if self.is_stopped: return False
            while self.is_paused:
                if self.is_stopped: return False
                time.sleep(0.1)
            time.sleep(0.1)
        return True

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.config(text="▶ RESUME" if self.is_paused else "⏸ PAUSE")
        self.progress_bar.config(style="Yellow.Horizontal.TProgressbar" if self.is_paused else "Green.Horizontal.TProgressbar")
        self.log("⏸ Translation paused. Waiting for active threads to finish..." if self.is_paused else "▶ Process resumed.")

    def stop_translation(self):
        if messagebox.askyesno("Stop", "Are you sure you want to stop the translation?"):
            self.is_stopped, self.is_paused = True, False
            self.btn_stop.config(state="disabled")
            self.btn_pause.config(state="disabled")
            self.log("⏹ Waiting for active requests to finish before stopping...")

    def reset_buttons(self):
        self.is_running = False
        self.btn_start.config(state="normal")
        self.btn_pause.config(state="disabled", text="⏸ PAUSE")
        self.btn_stop.config(state="disabled")
        self.progress_bar.config(style="Green.Horizontal.TProgressbar")

    def _load_models_task(self, token):
        if not token: return

        def ui_start():
            self.btn_load.config(state="disabled")
            self.model_combo.set("Loading...")
            self.log("Fetching model list...")

        self.root.after(0, ui_start)

        try:
            self.client = genai.Client(api_key=token)
            models = self.client.models.list()
            valid = []

            for m in models:
                name = m.name.replace("models/", "")
                low = name.lower()
                if ("flash" in low or "pro" in low) and not any(x in low for x in ("image", "audio", "tts", "vision")):
                    valid.append(name)

            if valid:
                disp = [f"{m} (Recommended)" if "3.1-flash" in m.lower() else m for m in valid]
                default_idx = next((i for i, v in enumerate(disp) if "Recommended" in v), 0)

                def ui_success():
                    self.btn_load.config(state="normal")
                    self.model_combo.config(values=disp)
                    self.model_combo.current(default_idx)
                    self.log("Models successfully loaded.")
                    self.save_settings()

                self.root.after(0, ui_success)
            else:
                def ui_not_found():
                    self.btn_load.config(state="normal")
                    self.model_combo.set("No text models found")
                    self.log("No text models found.")

                self.root.after(0, ui_not_found)

        except Exception as e:
            err_msg = str(e)

            def ui_error():
                self.btn_load.config(state="normal")
                self.model_combo.set("Loading error")
                self.log(f"API Error: {err_msg}")

            self.root.after(0, ui_error)

    def open_prompt_editor(self):
        top = tk.Toplevel(self.root)
        top.withdraw()
        top.title("Prompt Editor")
        center_win(top, 700, 500)
        top.minsize(600, 400)
        top.transient(self.root)
        top.grab_set()

        f = ttk.Frame(top, padding=15)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="REQUIRED: Do not remove {lang} and {source_text} tags!", font=("Segoe UI", 9, "bold"),
                  foreground="#ff6b6b").pack(anchor="w", pady=5)

        self.prompt_text = tk.Text(f, wrap=tk.WORD, font=("Consolas", 10), relief="flat")
        self.prompt_text.pack(fill="both", expand=True, pady=5)
        self.prompt_text.insert("1.0", self.custom_prompt)

        btns = ttk.Frame(f)
        btns.pack(fill="x", pady=10)

        def reset_prompt():
            self.prompt_text.delete("1.0", tk.END)
            self.prompt_text.insert("1.0", DEF_PROMPT)

        def save_prompt():
            self.custom_prompt = self.prompt_text.get("1.0", tk.END).strip()
            self.save_settings()
            top.destroy()

        ttk.Button(btns, text="Reset to default", command=reset_prompt).pack(side="left")
        ttk.Button(btns, text="✔ Save", style="Accent.TButton", command=save_prompt).pack(side="right")

        if HAS_MODERN_UI: apply_sys_theme(top, self.current_theme)
        self.update_colors()
        top.deiconify()

    def _build_scroll_grid(self, parent, data, cols=3):
        canvas = tk.Canvas(parent, highlightthickness=0, bg=ttk.Style().lookup('TFrame', 'background'))
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind('<Enter>', lambda e: canvas.bind_all("<MouseWheel>", lambda ev: canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all("<MouseWheel>"))

        rows = math.ceil(len(data) / cols)
        for i, (code, name) in enumerate(data.items()):
            ttk.Checkbutton(inner, text=name, variable=self.custom_lang_vars[code]).grid(row=i % rows, column=i // rows, sticky="w", padx=15, pady=8)

    def open_custom_lang_window(self):
        self.lang_mode.set(3)
        top = tk.Toplevel(self.root)
        top.withdraw()
        top.title("Language Selection")
        center_win(top, 960, 550)
        top.minsize(850, 500)
        top.transient(self.root)
        top.grab_set()

        f_top = ttk.Frame(top, padding=10)
        f_top.pack(fill="x")

        def select_all(state):
            for v in self.custom_lang_vars.values(): v.set(state)

        ttk.Button(f_top, text="Select All", command=lambda: select_all(True)).pack(side="left", padx=5)
        ttk.Button(f_top, text="Clear All", command=lambda: select_all(False)).pack(side="left", padx=5)
        self.lbl_count = ttk.Label(f_top, text="Selected: 0", font=("Segoe UI", 10, "bold"))
        self.lbl_count.pack(side="right", padx=15)
        self.update_lang_count()

        nb = ttk.Notebook(top)
        nb.pack(fill="both", expand=True, padx=10, pady=5)
        f_all = ttk.Frame(nb, padding=10)
        nb.add(f_all, text="All languages")
        self._build_scroll_grid(f_all, dict(sorted(FLAT_LANGS.items(), key=lambda i: POP_ORDER.index(i[0]) if i[0] in POP_ORDER else 999)))

        for region, langs in LANG_DATA.items():
            f_reg = ttk.Frame(nb, padding=10)
            nb.add(f_reg, text=region)
            self._build_scroll_grid(f_reg, langs)

        def save_and_close():
            self.save_settings()
            top.destroy()

        ttk.Button(top, text="Save and Close", style="Accent.TButton", command=save_and_close).pack(pady=15)
        if HAS_MODERN_UI: apply_sys_theme(top, self.current_theme)
        top.deiconify()

    def start_translation(self):
        token = self.token_var.get().strip()
        if not token or not self.input_file or not self.output_dir:
            return messagebox.showwarning("Error", "Check API key, model, and file paths!")

        self.save_settings()
        mode = self.lang_mode.get()
        self.selected_languages = PRESET_MAIN if mode == 1 else ALL_LANG_CODES if mode == 2 else [c for c, v in self.custom_lang_vars.items() if v.get()]
        if not self.selected_languages: return messagebox.showwarning("Error", "No languages selected!")

        self.is_running, self.is_paused, self.is_stopped = True, False, False
        self.btn_start.config(state="disabled")
        self.btn_pause.config(state="normal", text="⏸ PAUSE")
        self.btn_stop.config(state="normal")
        self.progress_bar.config(style="Green.Horizontal.TProgressbar")

        threading.Thread(target=self.run_translation, args=(token,), daemon=True).start()

    def _worker(self, lang, src_txt, model, total, token):
        if self.is_stopped: return
        while self.is_paused and not self.is_stopped: time.sleep(0.2)
        if self.is_stopped: return

        l_name = FLAT_LANGS.get(lang, lang)
        self.log(f"▶ Started translating: {l_name}...")

        prompt = self.custom_prompt.replace("{lang}", lang).replace("{source_text}", src_txt)
        retries = 0
        thread_client = genai.Client(api_key=token)

        while retries < 3 and not self.is_stopped:
            try:
                start_t = time.time()
                resp = thread_client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
                )
                res = resp.text.strip()
                if '{' in res: res = res[res.find('{'):res.rfind('}') + 1]

                with open(os.path.join(self.output_dir, f"{lang}.json"), 'w', encoding='utf-8') as f:
                    json.dump(json.loads(res), f, ensure_ascii=False, indent=4)

                self.log(f"✔ Success: {l_name} ({time.time() - start_t:.1f}s)")
                break
            except Exception as e:
                retries += 1
                err = str(e)
                if "429" in err or "EXHAUSTED" in err:
                    self.log(f"⏳ Rate limit (429) for {l_name}. Waiting 30s... (Attempt {retries}/3)")
                    self.interruptible_sleep(30)
                elif "503" in err or "500" in err:
                    self.log(f"⏳ Server busy for {l_name}. Waiting 30s... (Attempt {retries}/3)")
                    self.interruptible_sleep(30)
                elif "Expecting" in err or "delimiter" in err or "JSON" in err:
                    self.log(f"⚠️ Invalid JSON structure returned for {l_name}. Retrying... (Attempt {retries}/3)")
                    self.interruptible_sleep(3)
                else:
                    self.log(f"❌ Error {l_name}: {err[:100]}... (Attempt {retries}/3)")
                    self.interruptible_sleep(5)

                if retries >= 3: self.log(f"⏭ SKIPPED: {l_name} (Failed after 3 attempts)")

        if not self.is_stopped:
            with self.lock:
                self.completed_tasks += 1
                c = self.completed_tasks

            def update_prog():
                self.progress_var.set(c)
                self.lbl_progress.config(text=f"Processed: {c} of {total}")

            self.root.after(0, update_prog)

    def run_translation(self, token):
        model, skip = self.model_combo.get().replace(" (Recommended)", ""), self.skip_existing_var.get()
        src_code = os.path.splitext(os.path.basename(self.input_file))[0].lower()
        threads_count = self.threads_var.get()

        self.log(f"=== START (Model: {model} | Threads: {threads_count}) ===")

        tasks = []
        for l in self.selected_languages:
            if l.lower() == src_code: self.log(f"Skipping: {l} (source)"); continue
            if skip and os.path.exists(os.path.join(self.output_dir, f"{l}.json")): continue
            tasks.append(l)

        if not tasks:
            def done_skip():
                self.progress_var.set(len(self.selected_languages))
                self.lbl_progress.config(text=f"Done: {len(self.selected_languages)}")
                self.reset_buttons()

            self.root.after(0, done_skip)
            self.log("=== ALL DONE (Nothing to translate) ===")
            return

        def init_prog():
            self.progress_bar.config(maximum=len(tasks))
            self.progress_var.set(0)
            self.lbl_progress.config(text=f"Processed: 0 of {len(tasks)}")

        self.root.after(0, init_prog)

        with open(self.input_file, 'r', encoding='utf-8') as f:
            src_txt = f.read()

        self.completed_tasks = 0
        self.lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=threads_count) as executor:
            for lang in tasks:
                executor.submit(self._worker, lang, src_txt, model, len(tasks), token)

        self.log("=== PROCESS STOPPED ===" if self.is_stopped else "=== PROCESS SUCCESSFULLY COMPLETED ===")
        self.root.after(0, self.reset_buttons)


if __name__ == "__main__":
    app = TranslatorApp(tk.Tk())
    app.root.mainloop()