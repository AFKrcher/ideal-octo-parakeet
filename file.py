import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json, os, webbrowser
from threading import Timer
from multiprocessing import Manager

DATA_FILE = "data.json"

# Helper functions to load, save, and open data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            data = json.load(file)
            data.setdefault("urls", [])
            data.setdefault("files", [])
            return data
    return {"urls": [], "files": []}

def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def open_path(path):
    if path.startswith("http"):
        webbrowser.open(path)
    else:
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {e}")

# GUI class
class URLManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MySA")
        self.data = load_data()
        self.timer_threads = []
        self.manager = Manager()
        self.windows = self.manager.dict()
        self.url_var = tk.StringVar()
        self.timer_var = tk.StringVar()
        self.create_widgets()
        self.create_table()

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        for i, (text, var) in enumerate([("URL:", self.url_var), ("Timer (min):", self.timer_var)]):
            ttk.Label(frame, text=text).grid(row=i, column=0, sticky=tk.W)
            ttk.Entry(frame, textvariable=var, width=50 if i == 0 else 10).grid(row=i, column=1, sticky=tk.W)

        buttons = [("Submit URL", self.add_url), ("Select File", self.select_file), ("Open All & Start Timers", self.open_in_browser),
                   ("Delete Selected", self.delete_selected)]
        self.open_selected_button = ttk.Button(frame, text="Open Selected", command=self.open_selected, state=tk.DISABLED)
        self.stop_button = ttk.Button(frame, text="Stop Timer", command=self.stop_timers, state=tk.DISABLED)

        for i, (text, cmd) in enumerate(buttons):
            ttk.Button(frame, text=text, command=cmd).grid(row=2, column=i, sticky=tk.W)
        self.open_selected_button.grid(row=2, column=len(buttons), sticky=tk.W)
        self.stop_button.grid(row=2, column=len(buttons)+1, sticky=tk.W)

    def create_table(self):
        self.table_frame = ttk.Frame(self.root)
        self.table_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.headers = ["Path", "Timer"]
        self.table = ttk.Treeview(self.table_frame, columns=self.headers, show="headings", selectmode="extended")
        for header in self.headers:
            self.table.heading(header, text=header)
            self.table.column(header, stretch=tk.YES)
        self.table.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.load_table_data()
        self.table.bind("<Double-1>", self.on_double_click)
        self.table.bind("<<TreeviewSelect>>", self.update_open_selected_button)

    def load_table_data(self):
        for row in self.table.get_children():
            self.table.delete(row)
        for data in self.data["urls"] + self.data["files"]:
            self.table.insert("", "end", values=(data.get("URL") or data.get("Path"), data["Timer"]))

    def save_table_data(self, event=None):
        self.data = {"urls": [], "files": []}
        for row in self.table.get_children():
            path, timer = self.table.item(row, "values")
            (self.data["urls"] if path.startswith("http") else self.data["files"]).append({"URL" if path.startswith("http") else "Path": path, "Timer": timer})
        save_data(self.data)

    def on_double_click(self, event):
        item = self.table.selection()[0]
        values = self.table.item(item, "values")
        self.edit_popup(values, item)

    def edit_popup(self, values, item):
        popup = tk.Toplevel(self.root)
        popup.title("Edit Entry")

        path_entry, timer_entry = tk.Entry(popup, width=50), tk.Entry(popup, width=10)
        path_entry.insert(0, values[0])
        timer_entry.insert(0, values[1])

        for i, (label_text, entry) in enumerate([("Path:", path_entry), ("Re-Open Timer (minutes, optional):", timer_entry)]):
            tk.Label(popup, text=label_text).grid(row=i, column=0)
            entry.grid(row=i, column=1)

        def save_changes():
            self.table.item(item, values=(path_entry.get(), timer_entry.get()))
            self.save_table_data()
            popup.destroy()

        tk.Button(popup, text="Save", command=save_changes).grid(row=2, column=0, columnspan=2)

    def add_url(self):
        url, timer = self.url_var.get(), self.timer_var.get() or "0"
        if not url:
            messagebox.showwarning("Warning", "URL cannot be empty")
            return
        self.data["urls"].append({"URL": url, "Timer": timer})
        save_data(self.data)
        self.load_table_data()
        self.url_var.set("")
        self.timer_var.set("")

    def select_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            timer = self.timer_var.get() or "0"
            self.data["files"].append({"Path": file_path, "Timer": timer})
            save_data(self.data)
            self.load_table_data()

    def open_in_browser(self):
        self.stop_button.config(state=tk.NORMAL)
        for data in self.data["urls"] + self.data["files"]:
            self.open_item(data.get("URL") or data.get("Path"), data["Timer"])

    def open_selected(self):
        self.stop_button.config(state=tk.NORMAL)
        for item in self.table.selection():
            path, timer = self.table.item(item, "values")
            self.open_item(path, timer)

    def open_item(self, path, timer):
        open_path(path)
        if int(timer) > 0:
            t = Timer(int(timer) * 60, self.open_item, [path, timer])
            t.start()
            self.timer_threads.append(t)

    def stop_timers(self):
        for t in self.timer_threads:
            t.cancel()
        self.timer_threads.clear()
        self.stop_button.config(state=tk.DISABLED)

    def delete_selected(self):
        for item in self.table.selection():
            self.table.delete(item)
        self.save_table_data()

    def update_open_selected_button(self, event):
        self.open_selected_button.config(state=tk.NORMAL if self.table.selection() else tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = URLManagerApp(root)
    root.mainloop()
