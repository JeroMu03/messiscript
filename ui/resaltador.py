from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class ResaltadorMessiScript(QSyntaxHighlighter):
  def __init__(self, parent=None):
    super().__init__(parent)
    self.reglas = []

    # Palabras clave del lenguaje
    fmt_kw = QTextCharFormat()
    fmt_kw.setForeground(QColor("#75AADB"))
    fmt_kw.setFontWeight(QFont.Weight.Bold)
    palabras_kw = ["INICIAR", "FIN", "VAR", "REPETIR", "MOVER", "PASE", "REMATAR"]
    for kw in palabras_kw:
        self.reglas.append((QRegularExpression(rf"\b{kw}\b"), fmt_kw))

    # Direcciones
    fmt_dir = QTextCharFormat()
    fmt_dir.setForeground(QColor("#FBBF24"))
    fmt_dir.setFontWeight(QFont.Weight.Bold)
    for d in ["DERECHA", "IZQUIERDA", "ARRIBA", "ABAJO"]:
        self.reglas.append((QRegularExpression(rf"\b{d}\b"), fmt_dir))

    # Números enteros
    fmt_num = QTextCharFormat()
    fmt_num.setForeground(QColor("#22C55E"))
    self.reglas.append((QRegularExpression(r"\b\d+\b"), fmt_num))

    # Comentarios //
    fmt_com = QTextCharFormat()
    fmt_com.setForeground(QColor("#9CA3AF"))
    fmt_com.setFontItalic(True)
    self.reglas.append((QRegularExpression(r"//[^\n]*"), fmt_com))

  def highlightBlock(self, text: str) -> None:
    for patron, formato in self.reglas:
      it = patron.globalMatch(text)
      while it.hasNext():
          match = it.next()
          self.setFormat(match.capturedStart(), match.capturedLength(), formato)