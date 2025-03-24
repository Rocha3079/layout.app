import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLineEdit, QListWidget,
                             QGraphicsScene, QGraphicsView, QGraphicsRectItem,
                             QDialog, QFormLayout, QDialogButtonBox, QGraphicsTextItem,
                             QInputDialog, QMessageBox, QGraphicsItemGroup, QMenuBar, QMenu, QAction, QFileDialog)  # Import QInputDialog para editar o nome
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QBrush, QColor, QFont, QPen, QDrag, QPixmap, QPainter, QTextOption
from typing import Optional, List
import requests
import threading
import random
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from PyQt5.QtWidgets import QListWidgetItem
from PyQt5.QtCore import QMimeData
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
import json

# FastAPI Backend (Mesmo código do backend)
app = FastAPI()
# Simulação de banco de dados
stores = {}
categories = {}
store_layouts = {}
class Store(BaseModel):
    id: int
    name: str
    num_columns: int
    modules_per_column: int

class Category(BaseModel):
    id: int
    name: str

class Module(BaseModel):
    module_id: int
    column: int
    row: int
    x: int
    y: int
    name: str
    category_id: Optional[int] = None
    width: int = 60
    height: int = 30
    rotation: int = 0  # Adicione este atributo

class StoreLayoutData(BaseModel):
    store_id: int
    columns: List[List[Module]]

@app.post("/store/")
def create_store(store: Store):
    """
    Cria uma nova loja com o layout inicial.

    Args:
        store (Store): Objeto Store contendo os detalhes da loja.

    Returns:
        dict: Mensagem de confirmação e detalhes da loja criada.
    """
    if store.id in stores:
        raise HTTPException(status_code=400, detail="Store ID já existe")
    stores[store.id] = store

    # Cria um layout inicial com colunas
    columns = []
    module_id_counter = 0
    for column_index in range(store.num_columns):
        column = []
        for row_index in range(store.modules_per_column):
            module = Module(
                module_id=module_id_counter,
                column=column_index,
                row=row_index,
                x=column_index * 70,
                y=row_index * 40,
                name=f"Module {module_id_counter}"
            )
            column.append(module)
            module_id_counter += 1
        columns.append(column)

    store_layouts[store.id] = StoreLayoutData(store_id=store.id, columns=columns).dict()
    return {"message": "Loja criada", "store": store}
def get_store_layout(store_id: int):
    """
    Obtém o layout da loja especificada pelo ID.

    Args:
        store_id (int): ID da loja.

    Returns:
        dict: Layout da loja.
    """
@app.post("/category/")
def create_category(category: Category):
    if category.id in categories:
        raise HTTPException(status_code=400, detail="ID de categoria já existe")
@app.put("/store-layout/{store_id}")
def update_store_layout(store_id: int, layout_data: StoreLayoutData):
    """
    Atualiza o layout da loja.

    Args:
        store_id (int): ID da loja a ser atualizada.
        layout_data (StoreLayoutData): Dados do layout da loja.

    Returns:
        dict: Mensagem de confirmação e detalhes do layout atualizado.
    """

@app.get("/store-layout/{store_id}")
def get_store_layout(store_id: int):
    if store_id not in store_layouts:
        raise HTTPException(status_code=404, detail="Layout não encontrado")
    return store_layouts[store_id]

@app.put("/store-layout/{store_id}")
def update_store_layout(store_id: int, layout_data: StoreLayoutData):
    if store_id not in stores:
        raise HTTPException(status_code=404, detail="Loja não encontrada")

    store_layouts[store_id] = layout_data.dict()
    return {"message": "Layout atualizado", "store_layout": layout_data}

#Calcula o share do layout
@app.get("/store-layout/{store_id}/share")
def get_store_layout_share(store_id: int):
    if store_id not in store_layouts:
        raise HTTPException(status_code=404, detail="Layout não encontrado")
    layout_data = store_layouts[store_id]
    store = stores[store_id]

    total_modules = store.num_columns * store.modules_per_column
    category_counts = {}
    columns = layout_data.get("columns", [])  # Extrai a lista de colunas

    for column in columns:  # Itera sobre as colunas
        for module in column:  # Itera sobre os módulos na coluna
            cat_id = module.get("category_id")
            if (cat_id):
                category_counts[cat_id] = category_counts.get(cat_id, 0) + 1 #Contabiliza

    participation = {cat_id: (count / total_modules) * 100 for cat_id, count in category_counts.items()} #calcula o share
    return participation

API_URL = "http://127.0.0.1:8000"

def run_fastapi():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

threading.Thread(target=run_fastapi, daemon=True).start()

# PyQt5 Frontend
class CategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar Categoria")
        layout = QFormLayout(self)

        self.id_edit = QLineEdit(self)
        self.name_edit = QLineEdit(self)

        layout.addRow("ID:", self.id_edit)
        layout.addRow("Nome:", self.name_edit)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        layout.addWidget(self.buttons)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def get_category_data(self):
        return {"id": self.id_edit.text(), "name": self.name_edit.text()}

class DraggableRect(QGraphicsRectItem):
    def __init__(self, module: Module):
        super().__init__(module.x, module.y, module.width, module.height)
        self.module = module
        self.setRect(0, 0, module.width, module.height)  # Define o tamanho do retângulo
        self.setFlag(QGraphicsRectItem.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)  # Aceita drops
        self.setBrush(QBrush(QColor("white")))
        self.text_item = QGraphicsTextItem(module.name, self)  # Texto
        self.text_item.setFont(QFont("Arial", 8))
        self.text_item.setDefaultTextColor(QColor("black"))
        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.text_item.document().setDefaultTextOption(text_option)
        self.text_item.setTextWidth(self.rect().width())
        self.center_text()

    def mousePressEvent(self, event):
        self.setSelected(True)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.center_text()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.center_text()

    def mouseDoubleClickEvent(self, event):
        # Abre uma caixa de diálogo para editar o nome
        view = self.scene().views()[0]  # Obtém a primeira view associada à cena
        parent_widget = view.parent()  # Pega o widget pai correto
        new_name, ok = QInputDialog.getText(parent_widget, "Editar Nome do Módulo", "Novo Nome:", QLineEdit.Normal, self.module.name)

        if ok and new_name:
            self.module.name = new_name  # Atualiza o nome no objeto Module
            self.text_item.setPlainText(new_name)  # Atualiza o texto
            self.center_text()  # Centraliza
            print(f"Nome do módulo {self.module.module_id} alterado para: {new_name}")

    def center_text(self):
        text_rect = self.text_item.boundingRect()
        rect = self.rect()
        x = rect.left() + (rect.width() - text_rect.width()) / 2
        y = rect.top() + (rect.height() - text_rect.height()) / 2
        self.text_item.setPos(x, y)

    def snap_to_grid(self):
        grid_size = 20  # Ajusta o tamanho da grade para 20 pixels
        x = round(self.x() / grid_size) * grid_size
        y = round(self.y() / grid_size) * grid_size
        self.setPos(x, y)
        self.module.x = x
        self.module.y = y

class StoreLayoutScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(QRectF(0, 0, 6000, 5500))  # Aumenta o espaço útil
        self.draw_grid()

    def draw_grid(self):
        grid_size = 20  # Ajusta o tamanho da grade para 20 pixels
        scene_rect = self.sceneRect()
        left = int(scene_rect.left()) - int(scene_rect.left()) % grid_size
        top = int(scene_rect.top()) - int(scene_rect.top()) % grid_size
        right = int(scene_rect.right())
        bottom = int(scene_rect.bottom())

        pen = QPen(QColor(200, 200, 200))  # Cor da grade
        for x in range(left, right, grid_size):
            self.addLine(x, scene_rect.top(), x, scene_rect.bottom(), pen)

        for y in range(top, bottom, grid_size):
            self.addLine(scene_rect.left(), y, scene_rect.right(), y, pen)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.snap_selected_items_to_grid()

    def snap_selected_items_to_grid(self):
        grid_size = 20  # Ajusta o tamanho da grade para 20 pixels
        selected_items = self.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            if isinstance(item, QGraphicsItemGroup):
                for child in item.childItems():
                    if isinstance(child, DraggableRect):
                        child.snap_to_grid()
            elif isinstance(item, DraggableRect):
                item.snap_to_grid()

class StoreLayoutView(QGraphicsView):
    def __init__(self, scene: StoreLayoutScene, parent=None):
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setScene(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

    def zoom_in(self):
        self.scale(1.25, 1.25)

    def zoom_out(self):
        self.scale(0.8, 0.8)

class DraggableCategory(QListWidgetItem):
    def __init__(self, category_id, category_name, parent=None):
        super().__init__(f"{category_name} ({category_id})", parent)
        self.category_id = category_id
        self.category_name = category_name

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            drag = QDrag(event.widget())
            mimeData = QMimeData()
            mimeData.setText(str(self.category_id)) # Passa o ID como texto
            mimeData.setData("application/x-category", str(self.category_id).encode())  # Para identificar o tipo
            pixmap = QPixmap(self.listWidget().visualItemRect(self).size())
            painter = QPainter(pixmap)
            painter.fillRect(pixmap.rect(), QColor("lightgray"))  # Cor de fundo do item
            painter.drawText(pixmap.rect(), Qt.AlignCenter, self.text())  # Desenha o texto
            painter.end()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos() - self.listWidget().visualItemRect(self).topLeft())
            drag.exec_(Qt.CopyAction | Qt.MoveAction)

class StoreLayoutApp(QWidget):
    def __init__(self):
        super().__init__()
        self.API_URL = "http://127.0.0.1:8000"
        self.setWindowTitle("Engenharia de Layout de Loja")
        self.store_id = None
        self.categories = {}
        self.modules = {}
        self.category_colors = {}

        self.initUI()

    def initUI(self):
        # Layout Principal
        main_layout = QHBoxLayout(self)

        # Left Side (Store and Category Management)
        left_layout = QVBoxLayout()

        # Store Management
        store_layout = QVBoxLayout()
        store_layout.addWidget(QLabel("Cod da Loja:"))
        self.store_id_edit = QLineEdit(self)
        store_layout.addWidget(self.store_id_edit)

        store_layout.addWidget(QLabel("Nome da Loja:"))
        self.store_name_edit = QLineEdit(self)
        store_layout.addWidget(self.store_name_edit)

        store_layout.addWidget(QLabel("Número de Colunas:"))
        self.num_columns_edit = QLineEdit(self)
        store_layout.addWidget(self.num_columns_edit)

        store_layout.addWidget(QLabel("Módulos por Coluna:"))
        self.modules_per_column_edit = QLineEdit(self)
        store_layout.addWidget(self.modules_per_column_edit)

        self.create_store_btn = QPushButton("Criar Loja", self)
        self.create_store_btn.clicked.connect(self.create_store)
        store_layout.addWidget(self.create_store_btn)
        left_layout.addLayout(store_layout)

        # Category Management
        category_layout = QVBoxLayout()
        self.add_category_btn = QPushButton("Adicionar Categoria", self)
        self.add_category_btn.clicked.connect(self.add_category)
        category_layout.addWidget(self.add_category_btn)

        self.category_list = QListWidget(self)
        self.category_list.setDragEnabled(True)  # Permite "drag" na lista
        left_layout.addLayout(category_layout)
        category_layout.addWidget(self.category_list)  # Exibe as categorias

        # Module Management
        module_layout = QVBoxLayout()
        self.add_module_btn = QPushButton("Incluir Módulo", self)
        self.add_module_btn.clicked.connect(self.add_module)
        module_layout.addWidget(self.add_module_btn)
        

        self.remove_module_btn = QPushButton("Excluir Módulo", self)
        self.remove_module_btn.clicked.connect(self.remove_module)
        module_layout.addWidget(self.remove_module_btn)
        left_layout.addLayout(module_layout)

        # Right Side (Store Layout Visualization)
        self.scene = StoreLayoutScene(self)
        self.view = StoreLayoutView(self.scene, self)
        self.view.setAcceptDrops(True)
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.view)

        # Adding layouts to main layout
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

        # Adicionar a barra de menu
        self.menu_bar = QMenuBar(self)
        self.layout().setMenuBar(self.menu_bar)

        # Adicionar menus
        file_menu = self.menu_bar.addMenu("Arquivo")
        edit_menu = self.menu_bar.addMenu("Editar")
        view_menu = self.menu_bar.addMenu("Visualizar")  # Adicionar menu de visualização

        # Adicionar ações ao menu Arquivo
        get_layout_action = QAction("Obter Layout", self)
        get_layout_action.triggered.connect(self.get_layout)
        file_menu.addAction(get_layout_action)

        save_layout_action = QAction("Salvar Layout", self)
        save_layout_action.triggered.connect(self.save_layout)
        file_menu.addAction(save_layout_action)

        save_as_pdf_action = QAction("Salvar como PDF", self)
        save_as_pdf_action.triggered.connect(self.save_as_pdf)
        file_menu.addAction(save_as_pdf_action)

        print_layout_action = QAction("Imprimir Layout", self)
        print_layout_action.triggered.connect(self.print_layout)
        file_menu.addAction(print_layout_action)

        show_share_action = QAction("Exibir Share", self)
        show_share_action.triggered.connect(self.show_layout_share)
        file_menu.addAction(show_share_action)

        save_as_json_action = QAction("Salvar como JSON", self)
        save_as_json_action.triggered.connect(self.save_as_json)
        file_menu.addAction(save_as_json_action)

        load_from_json_action = QAction("Carregar do JSON", self)
        load_from_json_action.triggered.connect(self.load_from_json)
        file_menu.addAction(load_from_json_action)

        # Adicionar ações ao menu Editar
        resize_text_action = QAction("Redimensionar Texto", self)
        resize_text_action.triggered.connect(self.resize_text)
        edit_menu.addAction(resize_text_action)

        rotate_text_action = QAction("Rotacionar Texto", self)
        rotate_text_action.triggered.connect(self.rotate_text)
        edit_menu.addAction(rotate_text_action)

        resize_module_action = QAction("Redimensionar Módulo", self)
        resize_module_action.triggered.connect(self.resize_module)
        edit_menu.addAction(resize_module_action)

        rotate_module_action = QAction("Rotacionar Módulo", self)
        rotate_module_action.triggered.connect(self.rotate_module)
        edit_menu.addAction(rotate_module_action)

        group_modules_action = QAction("Agrupar Módulos", self)
        group_modules_action.triggered.connect(self.group_modules)
        edit_menu.addAction(group_modules_action)

        ungroup_modules_action = QAction("Desagrupar Módulos", self)
        ungroup_modules_action.triggered.connect(self.ungroup_modules)
        edit_menu.addAction(ungroup_modules_action)

        # Adicionar ações ao menu Visualizar
        zoom_in_action = QAction("Aumentar Zoom", self)
        zoom_in_action.triggered.connect(self.view.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Diminuir Zoom", self)
        zoom_out_action.triggered.connect(self.view.zoom_out)
        view_menu.addAction(zoom_out_action)

    def create_store(self):
        store_id = self.store_id_edit.text()
        store_name = self.store_name_edit.text()
        num_columns = self.num_columns_edit.text()
        modules_per_column = self.modules_per_column_edit.text()

        try:
            num_columns = int(num_columns)
            modules_per_column = int(modules_per_column)
            response = requests.post(f"{self.API_URL}/store/", json={"id": int(store_id), "name": store_name, "num_columns": num_columns, "modules_per_column": modules_per_column})
            response.raise_for_status()
            print(response.json())
            # Atualiza a interface
            self.store_id = int(store_id)
            self.num_columns = num_columns
            self.modules_per_column = modules_per_column
            self.categories = {}
            self.category_list.clear()
            self.modules = {}
            self.category_colors = {}

            self.draw_store_layout()

        except requests.exceptions.RequestException as e:
            print(f"Erro ao criar loja: {e}")
        except ValueError:
            print("Número de corredores e módulos por corredor devem ser inteiros.")

    def add_category(self):
        dialog = CategoryDialog(self)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            category_data = dialog.get_category_data()
            try:
                response = requests.post(f"{self.API_URL}/category/", json={"id": int(category_data['id']), "name": category_data['name']})
                response.raise_for_status()
                print(response.json())

                cat_id = int(category_data['id'])
                cat_name = category_data['name']
                self.categories[cat_id] = cat_name
                self.category_colors[cat_id] = "#{:06x}".format(random.randint(0, 0xFFFFFF))

                item = DraggableCategory(cat_id, cat_name)  # Usando a classe DraggableCategory
                self.category_list.addItem(item)
            except requests.exceptions.RequestException as e:
                print(f"Erro ao adicionar categoria: {e}")
            except ValueError:
                print("ID da categoria deve ser um inteiro.")

    def draw_store_layout(self):
        if not self.store_id:
            print("Crie uma loja primeiro.")
            return

        # Limpa a cena
        self.scene.clear()
        self.modules = {}

        # Desenha a grade
        self.scene.draw_grid()

        # Obtém o layout da API
        try:
            response = requests.get(f"{self.API_URL}/store-layout/{self.store_id}")
            response.raise_for_status()
            data = response.json()
            self.update_layout_from_api(data)

        except requests.exceptions.RequestException as e:
            print(f"Erro ao obter o layout: {e}")

    def update_layout_from_api(self, data):
        if not self.store_id:
            print("Crie uma loja primeiro.")
            return

        # Limpa a cena atual
        self.scene.clear()
        self.modules = {}

        # Desenha a grade
        self.scene.draw_grid()

        # Obtém as colunas da API
        columns_data = data.get("columns", [])

        # Configuração dos módulos
        grid_size = 20

        for column_index, column_data in enumerate(columns_data):
            for module_data in column_data:
                module = Module(**module_data)
                rect = DraggableRect(module)
                rect.setPos(module.x, module.y)  # Define a posição do retângulo
                self.scene.addItem(rect)
                self.modules[module.module_id] = rect

                if module.category_id:
                    color = self.category_colors.get(module.category_id, "gray")
                    rect.setBrush(QBrush(QColor(color)))

    def save_layout(self):
        if not self.store_id:
            print("Crie uma loja primeiro.")
            return

        # Converte o layout para o formato da API
        columns_data = []
        for column_index in range(self.num_columns):
            column = []
            for module_id, rect in self.modules.items():
                module = rect.module
                column.append(module)
            columns_data.append(column)

        layout_data = StoreLayoutData(store_id=self.store_id, columns=columns_data)

        try:
            response = requests.put(f"{self.API_URL}/store-layout/{self.store_id}", json=layout_data.dict())
            response.raise_for_status()
            print(response.json())
        except requests.exceptions.RequestException as e:
            print(f"Erro ao salvar o layout: {e}")

    def show_layout_share(self):
        if not self.store_id:
            print("Crie uma loja primeiro.")
            return

        try:
            response = requests.get(f"{self.API_URL}/store-layout/{self.store_id}/share")
            response.raise_for_status()
            share_data = response.json()

            message = "Participação das Categorias:\n"
            for cat_id, share in share_data.items():
                cat_name = self.categories.get(cat_id, "Desconhecido")
                message += f"{cat_name} ({cat_id}): {share:.2f}%\n"

            msg_box = QMessageBox()
            msg_box.setWindowTitle("Share do Layout")
            msg_box.setText(message)
            msg_box.exec_()

        except requests.exceptions.RequestException as e:
            print(f"Erro ao obter o share do layout: {e}")

    def get_layout(self):
        if not self.store_id:
            print("Crie uma loja primeiro.")
            return

        try:
            response = requests.get(f"{self.API_URL}/store-layout/{self.store_id}")
            response.raise_for_status()
            data = response.json()
            self.update_layout_from_api(data)
        except requests.exceptions.RequestException as e:
            print(f"Erro ao obter o layout: {e}")

    # Métodos para redimensionar e rotacionar o texto
    def resize_text(self):
        try:
            size, ok = QInputDialog.getInt(self, "Redimensionar Texto", "Novo Tamanho:", min=1, max=100)
            if ok:
                for rect in self.scene.selectedItems():
                    if isinstance(rect, DraggableRect):
                        rect.text_item.setFont(QFont("Arial", size))
                        rect.center_text()
        except Exception as e:
            print(f"Erro ao redimensionar texto: {e}")

    def rotate_text(self):
        angle, ok = QInputDialog.getInt(self, "Rotacionar Texto", "Novo Ângulo:", min=0, max=360)
        if ok:
            for rect in self.scene.selectedItems():
                if isinstance(rect, DraggableRect):
                    rect.rotate_text(angle)

    def resize_module(self):
        width, ok_width = QInputDialog.getInt(self, "Redimensionar Módulo", "Nova Largura:", min=10, max=200)
        if not ok_width:
            return

        height, ok_height = QInputDialog.getInt(self, "Redimensionar Módulo", "Nova Altura:", min=10, max=200)
        if not ok_height:
            return

        for rect in self.scene.selectedItems():
            if isinstance(rect, DraggableRect):
                rect.prepareGeometryChange()
                rect.setRect(rect.rect().x(), rect.rect().y(), width, height)
                rect.module.width = width
                rect.module.height = height
                rect.center_text()

    def rotate_module(self):
        angle, ok = QInputDialog.getInt(self, "Rotacionar Módulo", "Novo Ângulo:", min=0, max=360)
        if ok:
            for rect in self.scene.selectedItems():
                if isinstance(rect, DraggableRect):
                    rect.setRotation(angle)
                    rect.module.rotation = angle

    def group_modules(self):
        selected_items = self.scene.selectedItems()
        if len(selected_items) > 1:
            group = QGraphicsItemGroup()
            for item in selected_items:
                if isinstance(item, DraggableRect):
                    group.addToGroup(item)
            self.scene.addItem(group)

    def ungroup_modules(self):
        selected_items = self.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, QGraphicsItemGroup):
                for child in item.childItems():
                    item.removeFromGroup(child)
                self.scene.removeItem(item)

    def add_module(self):
        if not self.store_id:
            print("Crie uma loja primeiro.")
            return

        # Adiciona um novo módulo na primeira coluna e na primeira linha disponível
        column_index = 0
        row_index = len(self.modules) // self.num_columns
        module_id = len(self.modules)
        module_width = 60  # Largura do módulo inicial
        module_height = 40  # Altura do módulo inicial
        grid_size = 20

        module = Module(
            module_id=module_id,
            column=column_index,
            row=row_index,
            x=column_index * (module_width + grid_size),
            y=row_index * (module_height + grid_size),
            name=f"Module {module_id}",
            width=module_width,
            height=module_height
        )
        self.modules[module_id] = module

        rect = DraggableRect(module)
        rect.setPos(module.x, module.y)  # Define a posição do retângulo
        self.scene.addItem(rect)

    def remove_module(self):
        selected_items = self.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, DraggableRect):
                module_id = item.module.module_id
                self.scene.removeItem(item)
                del self.modules[module_id]

    def save_as_pdf(self):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName("store_layout.pdf")

        painter = QPainter(printer)
        self.view.render(painter)
        painter.end()

        print("Layout salvo como PDF.")

    def print_layout(self):
        printer = QPrinter(QPrinter.HighResolution)
        print_dialog = QPrintDialog(printer, self)

        if print_dialog.exec_() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            self.view.render(painter)
            painter.end()

            print("Layout enviado para impressão.")

    def save_as_json(self):
        if not self.store_id:
            print("Crie uma loja primeiro.")
            return

        # Abre um diálogo para escolher o nome e o diretório do arquivo
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Salvar Layout como JSON", "", "JSON Files (*.json);;All Files (*)", options=options)
        if not file_name:
            return

        # Converte o layout para o formato da API
        columns_data = [[] for _ in range(self.num_columns)]
        for module_id, rect in self.modules.items():
            module = rect.module
            columns_data[module.column].append(module.dict())

        layout_data = StoreLayoutData(store_id=self.store_id, columns=columns_data)

        with open(file_name, "w") as json_file:
            json.dump(layout_data.dict(), json_file, indent=4)

        print(f"Layout salvo como JSON em {file_name}.")

    def load_from_json(self):
        # Abre um diálogo para escolher o arquivo JSON
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Carregar Layout do JSON", "", "JSON Files (*.json);;All Files (*)", options=options)
        if not file_name:
            return

        try:
            with open(file_name, "r") as json_file:
                layout_data = json.load(json_file)
                store_id = layout_data['store_id']
                num_columns = len(layout_data['columns'])
                modules_per_column = max(len(column) for column in layout_data['columns'])

                # Cria a loja automaticamente se não existir
                if store_id not in stores:
                    store = Store(id=store_id, name=f"Loja {store_id}", num_columns=num_columns, modules_per_column=modules_per_column)
                    stores[store_id] = store
                    store_layouts[store_id] = layout_data

                # Atualiza a interface do usuário
                self.store_id = store_id
                self.num_columns = num_columns
                self.modules_per_column = modules_per_column
                self.update_layout_from_api(layout_data)
                print(f"Layout carregado do JSON de {file_name}.")
        except FileNotFoundError:
            print("Arquivo JSON não encontrado.")
        except json.JSONDecodeError:
            print("Erro ao decodificar o arquivo JSON.")
        except Exception as e:
            print(f"Erro ao carregar layout do JSON: {e}")

    def snap_selected_items_to_grid(self):
        grid_size = 20  # Ajusta o tamanho da grade para 20 pixels
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            if isinstance(item, DraggableRect):
                item.snap_to_grid()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.snap_selected_items_to_grid()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    store_layout = StoreLayoutApp()
    store_layout.setWindowTitle("Store Layout")
    store_layout.setGeometry(100, 100, 1000, 700)
    store_layout.show()
    sys.exit(app.exec_())
    
print("Fim do código")
