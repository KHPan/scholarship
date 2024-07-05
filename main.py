import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow,
			QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from bs4 import BeautifulSoup
import requests
import webbrowser
import itertools
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class LineQTableWidget(QTableWidget):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.setMouseTracking(True)
		self.lastHoveredRow = None

	def mouseMoveEvent(self, event):
		index = self.indexAt(event.pos())
		row = index.row()

		if self.lastHoveredRow is not None and self.lastHoveredRow != row:
			self.removeRowHighlight(self.lastHoveredRow)

		if row >= 0 and row != self.lastHoveredRow:
			self.setRowHighlight(row)
			self.lastHoveredRow = row

		super().mouseMoveEvent(event)

	def leaveEvent(self, event):
		if self.lastHoveredRow is not None:
			self.removeRowHighlight(self.lastHoveredRow)
			self.lastHoveredRow = None
		super().leaveEvent(event)

	def setRowHighlight(self, row):
		lightBlueColor = QColor('lightblue')
		for column in range(self.columnCount()):
			item = self.item(row, column)
			if item:
				item.setBackground(lightBlueColor)

	def removeRowHighlight(self, row):
		for column in range(self.columnCount()):
			item = self.item(row, column)
			if item:
				item.setBackground(Qt.white)

class MyMainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.initUI()

	def initUI(self):
		self.setWindowTitle("獎學金程式")

		central_widget = QWidget(self)
		self.setCentralWidget(central_widget)
		mainLayout = QVBoxLayout(central_widget)

		url = r"https://advisory.ntu.edu.tw/CMS/Scholarship?pageId=232&keyword=&applicant_type=18&sort=f_apply_start_date&pageIndex=15&show_way=all"
		re = requests.get(url)
		soup = BeautifulSoup(re.text, "lxml")
		titles = [t.getText() for t in
			soup.find("div", class_="list-result").find("table")
				.find("thead").find_all("td")]
		
		url_parts = urlparse(url)
		query_params = parse_qs(url_parts.query)

		chart = []
		self.ids = []
		for page in itertools.count(1, 1):
			query_params["pageIndex"] = page
			new_query_string = urlencode(query_params, doseq=True)
			new_url_parts = url_parts._replace(query=new_query_string)
			new_url = urlunparse(new_url_parts)
			re = requests.get(new_url)
			soup = BeautifulSoup(re.text, "lxml")
			tbody = (soup.find("div", class_="list-result")
					.find("table").find("tbody"))
			now_chart = [[td.getText() for td in tr.find_all("td")]
				for tr in tbody.find_all("tr")]
			if len(now_chart) == 0:
				break
			chart.extend(now_chart)
			self.ids.extend([tr.get("id") for tr in tbody.find_all("tr")])
		self.table = LineQTableWidget(len(chart), len(titles), self)
		self.table.setHorizontalHeaderLabels(titles)
		self.table.verticalHeader().setVisible(False)
		for y, line in enumerate(chart):
			for x, cell in enumerate(line):
				self.table.setItem(y, x, QTableWidgetItem(cell))
		self.table.setSelectionBehavior(QTableWidget.SelectRows)
		self.table.cellClicked.connect(self.clickTable)
		mainLayout.addWidget(self.table)
	
	def clickTable(self, row, _):
		webbrowser.open(f"https://advisory.ntu.edu.tw/CMS/ScholarshipDetail?id={self.ids[row]}")

if __name__ == "__main__":
	app = QApplication(sys.argv)
	mainWindow = MyMainWindow()
	mainWindow.show()
	sys.exit(app.exec_())
