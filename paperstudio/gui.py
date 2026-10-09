"""No-extra-GUI-deps Tkinter interface. Runs on a background worker to keep UI responsive."""
import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .pipeline import discover, process_pdf
from .translate import Translator
from .engines import ENGINES, defaults


def main():
    root = tk.Tk()
    root.title("AcademicPDF Studio 0.4.2 — 学术文献翻译")
    root.geometry("780x600")
    input_var = tk.StringVar()
    output_var = tk.StringVar(value=str(Path.cwd() / "paperstudio_output"))
    backend_var = tk.StringVar(value="fitz")
    engine_var = tk.StringVar(value="ollama")
    model_var = tk.StringVar(value="qwen2.5:7b")
    mode_var = tk.StringVar(value="zh")
    url_var = tk.StringVar(value=defaults("ollama")["url"])
    api_key_var = tk.StringVar(value="")
    def sync_model(*_):
        spec = defaults(engine_var.get())
        model_var.set(spec["model"])
        url_var.set(spec["url"])
        api_key_var.set("")
    engine_var.trace_add("write", sync_model)
    pdf_layout_var = tk.StringVar(value="reflow")
    equation_var = tk.StringVar(value="off")
    vectors_var = tk.BooleanVar(value=True)
    tables_var = tk.BooleanVar(value=True)
    formats = {x: tk.BooleanVar(value=True) for x in ("md", "pdf", "txt")}
    progress_queue = queue.Queue()
    frm = ttk.Frame(root, padding=15)
    frm.pack(fill="both", expand=True)

    def browse_file():
        name = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if name:
            input_var.set(name)
    def browse_dir():
        name = filedialog.askdirectory()
        if name:
            input_var.set(name)
    def browse_out():
        name = filedialog.askdirectory()
        if name:
            output_var.set(name)

    ttk.Label(frm, text="学术 PDF 翻译与 Markdown 转换", font=("Arial", 17, "bold")).grid(row=0, column=0, columnspan=4, pady=(0,14))
    ttk.Label(frm, text="源 PDF / 文件夹").grid(row=1, column=0, sticky="w")
    ttk.Entry(frm, textvariable=input_var).grid(row=1, column=1, sticky="ew")
    ttk.Button(frm, text="PDF", command=browse_file).grid(row=1, column=2)
    ttk.Button(frm, text="文件夹", command=browse_dir).grid(row=1, column=3)
    ttk.Label(frm, text="输出文件夹").grid(row=2, column=0, sticky="w")
    ttk.Entry(frm, textvariable=output_var).grid(row=2, column=1, sticky="ew")
    ttk.Button(frm, text="选择", command=browse_out).grid(row=2, column=2, columnspan=2)
    for row, name, var, values in [(3,"解析后端",backend_var,("fitz","docling")),
             (4,"翻译引擎",engine_var,tuple(ENGINES)),
             (7,"输出模式",mode_var,("zh","bilingual"))]:
        ttk.Label(frm, text=name).grid(row=row, column=0, sticky="w")
        ttk.Combobox(frm, textvariable=var, values=values, state="readonly").grid(row=row,column=1, sticky="ew")
    def configure_engine():
        pop = tk.Toplevel(root)
        pop.title("翻译引擎配置（密钥仅本次会话有效）")
        pop.geometry("565x380")
        pop.transient(root)
        pop.grab_set()
        panel = ttk.Frame(pop, padding=18)
        panel.pack(fill="both", expand=True)
        items = [("翻译引擎", engine_var, "combo"), ("模型名称", model_var, "input"),
                 ("API / Ollama 地址", url_var, "input"), ("API Key（不保存）", api_key_var, "password")]
        for r, (label, var, mode) in enumerate(items):
            ttk.Label(panel, text=label).grid(row=r, column=0, sticky="w", pady=9)
            if mode == "combo":
                w = ttk.Combobox(panel, textvariable=var, values=tuple(ENGINES), state="readonly")
            else:
                w = ttk.Entry(panel, textvariable=var, show="*" if mode == "password" else "")
            w.grid(row=r, column=1, sticky="ew", padx=9)
        panel.columnconfigure(1, weight=1)
        ttk.Label(panel, text="本地免费：Ollama / Argos；LibreTranslate 可自建。DeepSeek / OpenAI 需计费密钥。",
                  foreground="#795500", wraplength=505).grid(row=4,column=0,columnspan=2,sticky="w",pady=7)
        status = tk.StringVar(value="点击测试会请求短文本，远程 API 可能计费。")
        ttk.Label(panel, textvariable=status, wraplength=505).grid(row=5,column=0,columnspan=2,sticky="w",pady=10)
        def test():
            eng, model, endpoint, secret = engine_var.get(), model_var.get(), url_var.get(), api_key_var.get()
            status.set("正在测试…")
            def worker():
                try:
                    from tempfile import TemporaryDirectory
                    with TemporaryDirectory(prefix="academicpdf-engine-test-") as folder:
                        t = Translator(eng, model, Path(folder) / "test.json", url=endpoint or None,
                                       api_key=secret, retries=0)
                        result = t.test_connection()
                    root.after(0, lambda: status.set("连接成功：" + result[:100]))
                except Exception as err:
                    message = str(err)[:150]
                    root.after(0, lambda: status.set("失败：" + message))
            threading.Thread(target=worker, daemon=True).start()
        ttk.Button(panel, text="测试连接 / 翻译", command=test).grid(row=6,column=0,pady=8)
        ttk.Button(panel, text="保存本次配置并关闭", command=pop.destroy).grid(row=6,column=1,sticky="e")

    ttk.Label(frm, text="模型名称").grid(row=5, column=0, sticky="w")
    ttk.Entry(frm, textvariable=model_var).grid(row=5,column=1,sticky="ew")
    ttk.Button(frm,text="⚙ 翻译引擎配置 / API Key",command=configure_engine).grid(row=5,column=2,columnspan=2,sticky="ew")
    ttk.Label(frm, text="接口地址(可选)").grid(row=6,column=0,sticky="w")
    ttk.Entry(frm, textvariable=url_var).grid(row=6,column=1,sticky="ew")
    ttk.Label(frm, text="导出格式").grid(row=8,column=0,sticky="w")
    row = ttk.Frame(frm)
    row.grid(row=8, column=1, sticky="w")
    for f, var in formats.items():
        ttk.Checkbutton(row,text=f.upper(),variable=var).pack(side="left",padx=6)
    ttk.Label(frm, text="本地免费：Ollama / Argos；商业 API 将发送待翻译文本。密钥不写入磁盘。", foreground="#945500").grid(row=9,column=0,columnspan=4,sticky="w",pady=6)
    ttk.Label(frm, text="PDF 排版模式").grid(row=10, column=0, sticky="w")
    ttk.Combobox(frm, textvariable=pdf_layout_var, values=("reflow","overlay"), state="readonly").grid(row=10,column=1,sticky="ew")
    ttk.Checkbutton(frm, text="矢量图捕获", variable=vectors_var).grid(row=10,column=2)
    ttk.Checkbutton(frm, text="跨页表拼接", variable=tables_var).grid(row=10,column=3)
    ttk.Label(frm, text="数学公式 OCR").grid(row=11, column=0, sticky="w")
    ttk.Combobox(frm, textvariable=equation_var, values=("off", "pix2tex"), state="readonly").grid(row=11,column=1,sticky="ew")
    ttk.Label(frm, text="pix2tex 需要单独安装模型", foreground="#945500").grid(row=11,column=2,columnspan=2,sticky="w")
    start = ttk.Button(frm, text="开始转换")
    start.grid(row=12,column=0,columnspan=4,sticky="ew",pady=12)
    progress = ttk.Progressbar(frm, mode="indeterminate")
    progress.grid(row=13,column=0,columnspan=4,sticky="ew")
    logs = tk.Text(frm, height=15, wrap="word")
    logs.grid(row=14,column=0,columnspan=4,sticky="nsew",pady=10)
    frm.columnconfigure(1,weight=1)
    frm.rowconfigure(14,weight=1)

    def poll():
        try:
            while True:
                ty, value = progress_queue.get_nowait()
                if ty == "log":
                    logs.insert("end", value + "\n")
                    logs.see("end")
                elif ty == "done":
                    progress.stop()
                    start.configure(state="normal")
                    if value:
                        messagebox.showerror("完成但有错误", value)
                    else:
                        messagebox.showinfo("转换完成", "输出文件已保存")
        except queue.Empty:
            pass
        root.after(150, poll)

    def run_job(config):
        try:
            pdfs = discover(config["input"])
            if not pdfs:
                raise ValueError("所选文件夹中没有 PDF")
            if not config["formats"]:
                raise ValueError("至少选择一种导出格式")
            errors = []
            for path in pdfs:
                try:
                    report = process_pdf(path, config["output"], backend=config["backend"],
                        engine=config["engine"], model=config["model"], mode=config["mode"],
                        url=config["url"], api_key=config["api_key"], formats=config["formats"],
                        pdf_layout=config["pdf_layout"], vector_figures=config["vector_figures"],
                        stitch_tables=config["stitch_tables"],
                        equation_ocr=config["equation_ocr"],
                        progress=lambda s: progress_queue.put(("log",s)))
                    if report["warnings"]:
                        errors.append(f"{path}: 发现 {len(report['warnings'])} 条需复核的告警；请查看 manifest.json（已继续导出可恢复内容）")
                except Exception as e:
                    errors.append(f"{path}: {e}")
            progress_queue.put(("done", "\n".join(errors)))
        except Exception as e:
            progress_queue.put(("done", str(e)))

    def start_job():
        config = {"input": input_var.get(), "output": output_var.get(),
                  "backend": backend_var.get(), "engine": engine_var.get(),
                  "model": model_var.get(), "mode": mode_var.get(),
                  "url": url_var.get() or None, "api_key": api_key_var.get() or None,
                  "formats": tuple(k for k,v in formats.items() if v.get()),
                  "equation_ocr": equation_var.get(),
                  "pdf_layout": pdf_layout_var.get(), "vector_figures": vectors_var.get(),
                  "stitch_tables": tables_var.get()}
        logs.delete("1.0", "end")
        start.configure(state="disabled")
        progress.start(10)
        threading.Thread(target=run_job, args=(config,), daemon=True).start()
    start.configure(command=start_job)
    root.after(150, poll)
    root.mainloop()


if __name__ == "__main__":
    main()
