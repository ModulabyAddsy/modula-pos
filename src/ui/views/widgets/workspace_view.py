# src/ui/views/widgets/workspace_view.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTabBar, QPushButton, QStackedWidget)
from PySide6.QtCore import Qt

class WorkspaceView(QWidget):
    """
    Panel central con una implementación de pestañas personalizada para
    control total sobre la visibilidad y el comportamiento.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WorkspaceView")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(0)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(10)

        self.tab_bar = QTabBar()
        self.tab_bar.setObjectName("WorkspaceTabBar")
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setMovable(True)
        self.tab_bar.setExpanding(False)

        self.add_tab_button = QPushButton("+")
        self.add_tab_button.setObjectName("AddTabButton")
        self.add_tab_button.setCursor(Qt.PointingHandCursor)

        toolbar_layout.addWidget(self.tab_bar)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.add_tab_button)

        self.content_stack = QStackedWidget()
        
        # El placeholder ahora es un miembro permanente del stack en el índice 0
        self.placeholder_widget = self._crear_placeholder()
        self.content_stack.addWidget(self.placeholder_widget)

        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.content_stack)

        # --- CONEXIONES CORREGIDAS ---
        self.tab_bar.tabCloseRequested.connect(self.cerrar_pestaña)
        self.tab_bar.currentChanged.connect(self._sincronizar_vista_con_pestaña) # Conexión a un manejador
        self.add_tab_button.clicked.connect(lambda: self.abrir_nuevo_modulo("Dashboard"))

        # Inicia con la pestaña Dashboard por defecto
        self.abrir_nuevo_modulo("Dashboard")

    def _crear_placeholder(self):
        """Función auxiliar para crear el widget de bienvenida/vacío."""
        widget = QWidget()
        widget.setObjectName("WorkspaceContent")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # --- PETICIÓN 1: Cambiamos el texto del panel en blanco ---
        label = QLabel("Bienvenido a Modula. Abre un módulo en el panel izquierdo para visualizar.")
        label.setStyleSheet("font-size: 16px; color: #6b7281;")
        layout.addWidget(label)
        return widget

    def _update_view(self):
        """Muestra el placeholder si no hay pestañas."""
        if self.tab_bar.count() == 0:
            self.content_stack.setCurrentWidget(self.placeholder_widget)
        
    def cerrar_pestaña(self, index):
        """Cierra la pestaña y su contenido asociado."""
        widget_a_cerrar = self.content_stack.widget(index + 1)
        self.content_stack.removeWidget(widget_a_cerrar)
        widget_a_cerrar.deleteLater()
        self.tab_bar.removeTab(index)
        self._update_view()
        
    def _crear_modulo_widget(self, nombre_modulo: str):
        """Función auxiliar para crear el widget de contenido de un módulo."""
        nuevo_modulo_widget = QWidget()
        nuevo_modulo_widget.setObjectName("WorkspaceContent")
        layout = QVBoxLayout(nuevo_modulo_widget)
        layout.setAlignment(Qt.AlignCenter)
        
        label_text = f"Contenido del Módulo: {nombre_modulo}"
        if nombre_modulo == "Dashboard":
             label_text = "Bienvenido a Modula"
        
        label = QLabel(label_text)
        label.setStyleSheet("font-size: 24px;")
        layout.addWidget(label)
        return nuevo_modulo_widget

    def _sincronizar_vista_con_pestaña(self, index):
        """Sincroniza el QStackedWidget con el QTabBar."""
        if index >= 0:
            # El índice del stack es el de la pestaña + 1 (porque el placeholder está en 0)
            self.content_stack.setCurrentIndex(index + 1)
        else:
            # Si no hay pestañas seleccionadas, mostramos el placeholder (índice 0)
            self.content_stack.setCurrentIndex(0)

    def reemplazar_pestaña_actual(self, nombre_modulo: str, widget_modulo: QWidget):
        """
        Maneja el clic sencillo: reemplaza el Dashboard o enfoca una pestaña existente.
        """
        # 1. Buscamos si el módulo ya está abierto en OTRA pestaña.
        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabText(i) == nombre_modulo:
                self.tab_bar.setCurrentIndex(i)
                return

        # 2. Si no está abierto, verificamos la pestaña actual.
        current_index = self.tab_bar.currentIndex()
        
        if current_index == -1:
            self.abrir_nuevo_modulo(nombre_modulo, widget_modulo)
            return
            
        # 3. Si la pestaña actual es un "Dashboard", la reemplazamos.
        if self.tab_bar.tabText(current_index) == "Dashboard":
            # --- LÓGICA CORREGIDA Y MÁS SEGURA ---
            
            # El índice del widget en el stack es el de la pestaña + 1
            widget_index_a_reemplazar = current_index + 1

            # Verificamos que el widget exista en esa posición antes de intentar borrarlo
            if widget_index_a_reemplazar < self.content_stack.count():
                widget_a_reemplazar = self.content_stack.widget(widget_index_a_reemplazar)
                self.content_stack.removeWidget(widget_a_reemplazar)
                widget_a_reemplazar.deleteLater()
            
            # Insertamos el nuevo widget en la misma posición del stack
            self.content_stack.insertWidget(widget_index_a_reemplazar, widget_modulo)
            
            # Actualizamos el texto de la pestaña y la seleccionamos
            self.tab_bar.setTabText(current_index, nombre_modulo)
            self.tab_bar.setCurrentIndex(current_index) # Esto activará la sincronización
            
            self.content_stack.setCurrentWidget(widget_modulo)


    def abrir_nuevo_modulo(self, nombre_modulo: str, widget_modulo: QWidget = None):
        """
        MODIFICADO: Ahora recibe el widget del módulo. Si no lo recibe, crea un placeholder.
        """
        if nombre_modulo != "Dashboard":
            for i in range(self.tab_bar.count()):
                if self.tab_bar.tabText(i) == nombre_modulo:
                    self.tab_bar.setCurrentIndex(i)
                    return

        if self.tab_bar.count() == 0:
            if self.content_stack.indexOf(self.placeholder_widget) != -1:
                self.content_stack.removeWidget(self.placeholder_widget)

        # Si no nos pasan un widget, creamos uno de bienvenida (para el Dashboard)
        if not widget_modulo:
             widget_modulo = self._crear_modulo_widget(nombre_modulo)
        
        index = self.tab_bar.addTab(nombre_modulo)
        self.content_stack.addWidget(widget_modulo)
        self.tab_bar.setCurrentIndex(index)