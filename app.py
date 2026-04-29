import os
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "<h1>Tehillim</h1><p>Em construção. Acesse <a href='/staging'>/staging</a> para o ambiente de teste.</p>"


@app.route("/staging")
def staging():
    return """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tehillim — Staging</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-[#FAF7F2] flex items-center justify-center">
  <div class="text-center">
    <div class="w-20 h-20 rounded-full border-4 border-gray-800 flex items-center justify-center mx-auto mb-6">
      <span style="font-size:48px;font-family:'Georgia',serif;color:#1f2937;line-height:1;">&#119070;</span>
    </div>
    <p class="text-xs tracking-[4px] text-gray-400 uppercase mb-2">TEHILLIM</p>
    <h1 class="text-3xl font-bold text-gray-800 mb-3">Staging funcionando!</h1>
    <p class="text-gray-500 mb-6">A plataforma está no ar. O conteúdo completo em breve.</p>
    <span class="inline-block bg-green-100 text-green-700 text-xs font-semibold px-3 py-1 rounded-full">✓ Cloud Run ativo</span>
  </div>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
