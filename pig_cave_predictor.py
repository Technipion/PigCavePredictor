import json
import urllib.request
from datetime import datetime, timedelta
from dataclasses import dataclass
from tkinter import Tk, StringVar, Toplevel, END, VERTICAL
from tkinter import font
from tkinter import ttk


SCORE_THRESHOLD = 0.8


def main():
    statuses = []

    root = Tk()
    root.title("Pig Cave Next Opening Time Predictor for EU Region")

    s = ttk.Style()
    if "clam" in s.theme_names():
        s.theme_use("clam")
    s.configure("Treeview", rowheight=20)

    helvetica = font.Font(family="Helvetica", size=12, weight="bold")

    content = ttk.Frame(root, padding=15)

    last_close_time_str = StringVar()
    predicted_open_time_str = StringVar()
    predicted_timeframe_str = StringVar()

    lct_lbl = ttk.Label(content, font=helvetica,
                        text="Last closing time:")
    pot_lbl = ttk.Label(content, font=helvetica,
                        text="Predicted next open time:")
    ptf_lbl = ttk.Label(content, font=helvetica,
                        text="Predicted next open timeframe:")
    lct_val = ttk.Label(content, font=helvetica,
                        textvariable=last_close_time_str)
    pot_val = ttk.Label(content, font=helvetica,
                        textvariable=predicted_open_time_str)
    ptf_val = ttk.Label(content, font=helvetica,
                        textvariable=predicted_timeframe_str)

    def command_details():
        secondary_window = Toplevel()
        secondary_window.title("Data")
        secondary_window.config(width=600, height=400)

        content = ttk.Frame(secondary_window, padding=15)

        tree = ttk.Treeview(content, column=("timestamp", "status",
                            "yes_count", "no_count", "score"),
                            show="headings")

        tree.heading("timestamp", text="Timestamp")
        tree.heading("status", text="Status")
        tree.heading("yes_count", text="Votes Yes")
        tree.heading("no_count", text="Votes No")
        tree.heading("score", text="Score")

        tree.column("timestamp", width=400, anchor="e")
        tree.column("status", width=150, anchor="w")
        tree.column("yes_count", width=150, anchor="center")
        tree.column("no_count", width=150, anchor="center")
        tree.column("score", width=150, anchor="center")

        for i, status in enumerate(statuses):
            values = (timestamp_to_str(status.timestamp),
                      "open" if status.open else "closed",
                      str(status.yes_count),
                      str(status.no_count),
                      f"{status.get_score():.3f}")
            tree.insert('', END, values=values)

        content.grid(column=0, row=0, sticky="nsew")
        tree.grid(column=0, row=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(content, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(column=1, row=0, sticky="ns")

        secondary_window.columnconfigure(0, weight=1)
        secondary_window.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1, minsize=600)
        content.rowconfigure(0, weight=1, minsize=400)

    details_button = ttk.Button(content, text="Show data",
                                command=command_details)
    details_button.state(["disabled"])

    def command_fetch():
        last_close_time_str.set("fetching...")
        predicted_open_time_str.set("fetching...")
        predicted_timeframe_str.set("fetching...")

        url = "https://api.garmoth.com/api/golden-pig-cave-reports?region=eu"
        data = fetch_json(url)

        for entry in data["reports"]:
            if "status" not in entry:
                continue

            timestamp = datetime.fromisoformat(entry["created_at"])
            open = True if entry["status"] == "open" else False
            yes_count = int(entry["yes_count"])
            no_count = int(entry["no_count"])

            statuses.append(CaveStatus(timestamp, open, yes_count, no_count))

        statuses.sort(key=lambda s: s.timestamp, reverse=True)

        last_close_time = None
        for status in statuses:
            if not status.open and status.get_score() > SCORE_THRESHOLD:
                last_close_time = status.timestamp
                break

        if last_close_time is None:
            print("Could not retrieve valid value for last closing time.")
            return

        (predicted_open_time,
         likely_open_time_start,
         likely_open_time_end) = predict_timeframe(last_close_time)

        last_close_time_str.set(timestamp_to_str(last_close_time))
        predicted_open_time_str.set(timestamp_to_str(predicted_open_time))
        predicted_timeframe_str.set(
            timestamp_to_str(likely_open_time_start) + "\n" +
            timestamp_to_str(likely_open_time_end)
        )

        details_button.state(["!disabled"])

    fetch_button = ttk.Button(content, text="Recalculate",
                              command=command_fetch)
    fetch_button.state(["focus"])

    content.grid(column=0, row=0)

    lct_lbl.grid(column=0, row=0, sticky="e")
    pot_lbl.grid(column=0, row=1, sticky="e")
    ptf_lbl.grid(column=0, row=2, sticky="e")
    lct_val.grid(column=1, row=0)
    pot_val.grid(column=1, row=1)
    ptf_val.grid(column=1, row=2)
    fetch_button.grid(column=0, row=3, pady=10)
    details_button.grid(column=1, row=3, pady=10)

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    content.columnconfigure(0, weight=1, minsize=300)
    content.columnconfigure(1, weight=1, minsize=300)
    content.rowconfigure(0, weight=1, minsize=30)
    content.rowconfigure(1, weight=1, minsize=30)
    content.rowconfigure(2, weight=1, minsize=50)
    content.rowconfigure(3, weight=1, minsize=30)

    root.mainloop()


def predict_timeframe(last_close_time: datetime) -> tuple:
    average_time_difference = 11  # in hours
    time_difference_variation = 2  # in hours

    predicted_open_time = last_close_time + \
        timedelta(hours=average_time_difference)
    likely_open_time_start = predicted_open_time - \
        timedelta(hours=time_difference_variation)
    likely_open_time_end = predicted_open_time + \
        timedelta(hours=time_difference_variation)

    return predicted_open_time, likely_open_time_start, likely_open_time_end


def fetch_json(url):
    req = urllib.request.Request(url)
    req.add_header('User-Agent',
                   'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0')
    req.add_header('Accept',
                   'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8')
    req.add_header('Accept-Language',
                   'en-US,en;q=0.5')

    response = urllib.request.urlopen(req).read().decode('utf-8')
    return json.loads(response)


@dataclass
class CaveStatus:
    """Class for keeping track of cave opening and closing events."""
    timestamp: datetime
    open: bool  # True: opened, False: closed
    yes_count: int  # voting
    no_count: int  # voting

    def get_score(self) -> float:
        total = self.yes_count + self.no_count
        return (self.yes_count - self.no_count) / total


def timestamp_to_str(timestamp: datetime) -> str:
    """Converts given timestamp to str."""

    return f"{timestamp.astimezone():%Y-%m-%d %H:%M}"  # ISO short
    # return timestamp.astimezone().isoformat()  # ISO
    # return f"{timestamp.astimezone():%d.%m.%Y %H:%M}"  # german


if __name__ == "__main__":
    main()
