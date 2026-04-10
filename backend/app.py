#!/usr/bin/env python3
import os
import re
import json
import urllib.parse
import mimetypes
from flask import Flask, jsonify, send_from_directory, request, make_response, Response

app = Flask(__name__, static_folder="../frontend", static_url_path="/static")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/api/memory/graph")
def api_mem_graph():
    from memo_utils import build_memory_graph
    try:
        return jsonify(build_memory_graph())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/memory/content")
def api_mem_content():
    node_id = request.args.get("id")
    if not node_id: return jsonify({"error": "No ID"}), 400
    decoded_id = urllib.parse.unquote(node_id).strip()
    from memo_utils import get_all_md_files
    files = get_all_md_files()
    
    target_path = None
    for p in files:
        fname = os.path.basename(p).replace(".md", "").strip()
        if fname == decoded_id or fname.replace(" ","") == decoded_id.replace(" ","") or fname == node_id:
            target_path = p
            break
            
    if not target_path or not os.path.exists(target_path):
        return jsonify({"error": f"Not Found: {decoded_id}"}), 404
    
    # 查找关联的原始 PDF
    # 原理：假设 PDF 在同一个目录下，或者父目录的 raw 下，且文件名相同
    pdf_path = None
    base_dir = os.path.dirname(target_path)
    base_name = os.path.basename(target_path).replace(".md", "")
    
    possible_pdfs = [
        os.path.join(base_dir, base_name + ".pdf"),
        os.path.join(os.path.dirname(base_dir), base_name + ".pdf"),
        os.path.join(base_dir, "raw", base_name + ".pdf")
    ]
    for p_pdf in possible_pdfs:
        if os.path.exists(p_pdf):
            pdf_path = p_pdf
            break

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 简单的图片链接处理
        def safe_replace_img(match):
            try:
                alt, img_p = match.group(1), match.group(2)
                img_p_u = urllib.parse.unquote(img_p)
                full_p = img_p_u if ":" in img_p_u else os.path.abspath(os.path.join(base_dir, img_p_u))
                return f'![{alt}](/api/memory/image?path={urllib.parse.quote(full_p)})'
            except: return match.group(0)

        content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', safe_replace_img, content)
        
        return jsonify({
            "id": decoded_id, 
            "content": content, 
            "pdf_link": f"/api/memory/pdf?path={urllib.parse.quote(pdf_path)}" if pdf_path else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/memory/pdf")
def api_mem_pdf():
    p = request.args.get("path")
    if not p: return "400", 400
    p = os.path.normpath(urllib.parse.unquote(p))
    if os.path.exists(p) and p.lower().endswith(".pdf"):
        return send_from_directory(os.path.dirname(p), os.path.basename(p))
    return "404", 404

@app.route("/api/memory/image")
def api_mem_image():
    p = request.args.get("path")
    if not p: return "400", 400
    p = os.path.normpath(urllib.parse.unquote(p))
    if os.path.exists(p):
        mime, _ = mimetypes.guess_type(p)
        with open(p, "rb") as f:
            return Response(f.read(), mimetype=mime or "application/octet-stream")
    return "404", 404

@app.route("/memory-graph")
def mem_graph_page():
    return send_from_directory(FRONTEND_DIR, "memory_graph.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=19000)
