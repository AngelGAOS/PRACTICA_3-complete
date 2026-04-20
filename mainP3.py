import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import time
import xml.etree.ElementTree as ET

# ==========================================
# CEREBRO MATEMÁTICO: MOTOR AFN / AFN-λ / MINIMIZACIÓN
# ==========================================
class MotorAutomata:
    def __init__(self, datos_json):
        self.inicial = datos_json.get('inicial', '')
        self.finales = set(datos_json.get('finales', []))
        self.alfabeto = set(datos_json.get('alfabeto', []))
        self.transiciones = {}
        
        for estado in datos_json.get('estados', []):
            self.transiciones[estado['id']] = {}
            
        for t in datos_json.get('transiciones', []):
            origen = t['de']
            destino = t['a']
            simbolo = t['lee']
            
            if simbolo not in self.transiciones[origen]:
                self.transiciones[origen][simbolo] = set()
            self.transiciones[origen][simbolo].add(destino)

    def clausura_lambda(self, estados_actuales):
        clausura = set(estados_actuales)
        pila = list(estados_actuales)
        
        while pila:
            estado_actual = pila.pop()
            if 'λ' in self.transiciones.get(estado_actual, {}):
                destinos_lambda = self.transiciones[estado_actual]['λ']
                for destino in destinos_lambda:
                    if destino not in clausura:
                        clausura.add(destino)
                        pila.append(destino)
        return clausura

    def mover(self, estados_actuales, simbolo):
        destinos = set()
        for estado in estados_actuales:
            if simbolo in self.transiciones.get(estado, {}):
                destinos.update(self.transiciones[estado][simbolo])
        return destinos

    def simular_cadena_paso_a_paso(self, cadena):
        historial = []
        estados_activos = self.clausura_lambda({self.inicial})
        
        historial.append({
            "paso": 0,
            "simbolo": "INICIO (λ)",
            "estados_activos": sorted(list(estados_activos))
        })
        
        for i, simbolo in enumerate(cadena):
            estados_alcanzados = self.mover(estados_activos, simbolo)
            estados_activos = self.clausura_lambda(estados_alcanzados)
            
            historial.append({
                "paso": i + 1,
                "simbolo": simbolo,
                "estados_activos": sorted(list(estados_activos)) if estados_activos else ["Ø (Muerte)"]
            })
            if not estados_activos:
                break
                
        es_aceptada = bool(estados_activos.intersection(self.finales))
        return es_aceptada, historial

    def minimizar_afd(self):
        """ Ejecuta el algoritmo de clases de equivalencia para minimizar el AFD """
        # 1. Eliminar inalcanzables (Búsqueda en grafo)
        alcanzables = set([self.inicial])
        pila = [self.inicial]
        while pila:
            est = pila.pop()
            for sim in self.alfabeto:
                dest = list(self.transiciones.get(est, {}).get(sim, set()))
                if dest and dest[0] not in alcanzables:
                    alcanzables.add(dest[0])
                    pila.append(dest[0])

        estados_eliminados = set(self.transiciones.keys()) - alcanzables

        # 2. Inicializar particiones (Aceptación vs No Aceptación)
        f_alcanzables = self.finales.intersection(alcanzables)
        nf_alcanzables = alcanzables - f_alcanzables

        particiones = []
        if f_alcanzables: particiones.append(f_alcanzables)
        if nf_alcanzables: particiones.append(nf_alcanzables)

        # 3. Refinar particiones (Separar por comportamiento)
        cambio = True
        while cambio:
            cambio = False
            nuevas_particiones = []
            for grupo in particiones:
                if len(grupo) <= 1:
                    nuevas_particiones.append(grupo)
                    continue

                subgrupos = {}
                for estado in grupo:
                    firma = []
                    for sim in sorted(list(self.alfabeto)):
                        destinos = list(self.transiciones.get(estado, {}).get(sim, set()))
                        destino = destinos[0] if destinos else None
                        idx = -1
                        for i, p in enumerate(particiones):
                            if destino in p:
                                idx = i
                                break
                        firma.append(idx)
                    firma = tuple(firma)
                    if firma not in subgrupos:
                        subgrupos[firma] = set()
                    subgrupos[firma].add(estado)

                nuevas_particiones.extend(subgrupos.values())
                if len(subgrupos) > 1:
                    cambio = True
            particiones = nuevas_particiones

        # 4. Construir Autómata Minimizado para la interfaz
        nuevas_transiciones = []
        nombres_grupos = {}

        # Nombrar a los nuevos grupos (Fusionando sus IDs originales)
        for grupo in particiones:
            nombre = "q{" + ",".join(sorted(list(grupo))) + "}"
            for est in grupo:
                nombres_grupos[est] = nombre

        # Mapear las transiciones de los nuevos estados fusionados
        for grupo in particiones:
            rep = list(grupo)[0] # Tomamos a un representante del grupo
            origen = nombres_grupos[rep]
            for sim in sorted(list(self.alfabeto)):
                destinos = list(self.transiciones.get(rep, {}).get(sim, set()))
                if destinos:
                    dest = destinos[0]
                    nuevas_transiciones.append({
                        "de": origen,
                        "lee": sim,
                        "a": nombres_grupos[dest]
                    })

        return {
            "eliminados": estados_eliminados,
            "particiones": particiones,
            "nuevas_transiciones": nuevas_transiciones
        }
    
    def convertir_afnd_a_afd(self):
        """ Ejecuta el algoritmo de subconjuntos para convertir AFND/AFN-λ a AFD """
        # Filtramos lambda del alfabeto para las transiciones del AFD
        alfabeto_real = sorted([s for s in self.alfabeto if s != 'λ'])
        
        # 1. El estado inicial del AFD es la λ-clausura del estado inicial del AFN
        inicial_afd = frozenset(self.clausura_lambda({self.inicial}))
        
        estados_afd = [inicial_afd] # Lista de todos los súper-estados descubiertos
        pila_procesamiento = [inicial_afd] # Pila para procesar nuevos estados
        transiciones_afd = []
        
        # 2. Algoritmo de exploración de subconjuntos
        while pila_procesamiento:
            estado_actual = pila_procesamiento.pop(0)
            
            for sim in alfabeto_real:
                # Paso A: Mover (alcanzables consumiendo el símbolo)
                alcanzables = self.mover(estado_actual, sim)
                
                # Si no llegamos a nada, ignoramos (actúa como sumidero implícito)
                if not alcanzables:
                    continue 
                    
                # Paso B: Aplicar λ-clausura a los alcanzables
                destino_clausura = frozenset(self.clausura_lambda(alcanzables))
                
                # Guardar la transición calculada
                transiciones_afd.append({
                    "de": estado_actual,
                    "lee": sim,
                    "a": destino_clausura
                })
                
                # Si descubrimos un Súper-Estado nuevo, lo agregamos para analizarlo después
                if destino_clausura not in estados_afd:
                    estados_afd.append(destino_clausura)
                    pila_procesamiento.append(destino_clausura)
                    
        # 3. Determinar los estados de aceptación del nuevo AFD
        finales_afd = [est for est in estados_afd if est.intersection(self.finales)]
        
        return {
            "inicial": inicial_afd,
            "estados": estados_afd,
            "transiciones": transiciones_afd,
            "finales": finales_afd,
            "alfabeto": alfabeto_real
        }

# ==========================================
# APLICACIÓN PRINCIPAL (GUI)
# ==========================================
def main():
    root = tk.Tk()
    root.title("Simulador Avanzado AFD/AFN - Proyecto TC")
    root.geometry("1050x750")
    root.eval('tk::PlaceWindow . center')
    root.configure(bg="#f0f2f5")

    style = ttk.Style()
    style.theme_use('clam') 
    style.configure("TFrame", background="#f0f2f5")
    style.configure("TLabel", background="#f0f2f5", font=("Segoe UI", 10))
    style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1a365d")
    style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6, background="#2b6cb0", foreground="white")
    style.map("TButton", background=[("active", "#2c5282")])
    style.configure("TLabelframe", background="#ffffff", borderwidth=2)
    style.configure("TLabelframe.Label", font=("Segoe UI", 11, "bold"), foreground="#2d3748", background="#ffffff")
    style.configure("Treeview", font=("Consolas", 10), rowheight=30, borderwidth=0)
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e2e8f0", foreground="#1a202c")
    style.map("Treeview", background=[("selected", "#bee3f8")], foreground=[("selected", "#2b6cb0")])

    # Guardamos los datos crudos también para mostrarlos en la Pestaña 3
    app_state = {"motor": None, "datos_json": None}

    def escribir_consola(mensaje):
        consola.config(state=tk.NORMAL)
        consola.insert(tk.END, f"> {mensaje}\n")
        consola.see(tk.END)
        consola.config(state=tk.DISABLED)
        root.update()
        time.sleep(0.05)

    def cargar_archivo():
        ruta = filedialog.askopenfilename(
            title="Descubre tu Autómata", 
            filetypes=[
                ("Todos los soportados", "*.jff *.json *.xml"),
                ("Archivos JFLAP", "*.jff"),
                ("Archivos JSON", "*.json"),
                ("Archivos XML", "*.xml")
            ]
        )
        if not ruta: return
            
        try:
            consola.config(state=tk.NORMAL)
            consola.delete(1.0, tk.END)
            consola.config(state=tk.DISABLED)
            
            escribir_consola(f"Iniciando análisis del archivo: {ruta.split('/')[-1]}...")
            
            datos = {}
            if ruta.endswith('.json'):
                with open(ruta, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                escribir_consola("JSON descifrado con éxito.")
                
            elif ruta.endswith('.jff') or ruta.endswith('.xml'):
                escribir_consola("Detectado formato XML/JFLAP. Parseando nodos...")
                tree = ET.parse(ruta)
                root_xml = tree.getroot()
                automaton = root_xml.find('automaton')
                
                datos = {
                    'estados': [],
                    'transiciones': [],
                    'inicial': '',
                    'finales': [],
                    'alfabeto': set()
                }
                
                for state in automaton.findall('state'):
                    id_estado = state.get('id')
                    nombre = state.get('name')
                    datos['estados'].append({'id': id_estado, 'nombre': nombre})
                    
                    if state.find('initial') is not None:
                        datos['inicial'] = id_estado
                    if state.find('final') is not None:
                        datos['finales'].append(id_estado)
                        
                for trans in automaton.findall('transition'):
                    origen = trans.find('from').text
                    destino = trans.find('to').text
                    read_tag = trans.find('read')
                    lee = read_tag.text if read_tag is not None and read_tag.text else 'λ'
                    
                    datos['transiciones'].append({'de': origen, 'lee': lee, 'a': destino})
                    if lee != 'λ':
                        datos['alfabeto'].add(lee)
                        
                datos['alfabeto'] = list(datos['alfabeto'])
                escribir_consola("Archivo JFLAP traducido a modelo lógico.")

            app_state["datos_json"] = datos
            app_state["motor"] = MotorAutomata(datos)
            
            alfabeto = datos.get('alfabeto', [])
            escribir_consola(f"Extrayendo alfabeto Σ = {{ {', '.join(alfabeto)} }}")
            lbl_alfabeto.config(text=f"Σ = {{ {', '.join(alfabeto)} }}")
            
            nombres_estados = [e['nombre'] for e in datos.get('estados', [])]
            escribir_consola(f"Identificando Q... ({len(nombres_estados)} encontrados)")
            lbl_estados.config(text=f"Q = {{ {', '.join(nombres_estados)} }}")
            lbl_inicial.config(text=f"q0 = {datos.get('inicial', '')}")
            lbl_finales.config(text=f"F = {{ {', '.join(datos.get('finales', []))} }}")
            
            for item in tabla_transiciones.get_children(): tabla_transiciones.delete(item)
                
            escribir_consola("Mapeando función de transición δ...")
            for i, t in enumerate(datos.get("transiciones", [])):
                tag = 'par' if i % 2 == 0 else 'impar'
                tabla_transiciones.insert("", tk.END, values=(f"δ({t['de']}, {t['lee']})", "→", t["a"]), tags=(tag,))
            
            for item in tabla_orig.get_children(): tabla_orig.delete(item)
            for item in tabla_mini.get_children(): tabla_mini.delete(item)
            lbl_stats_min.config(text="Esperando ejecución...")

            escribir_consola("¡Autómata ensamblado y listo para simular!")
            messagebox.showinfo("Éxito", "El autómata ha sido cargado.")
            
        except Exception as e:
            escribir_consola(f"[ERROR CRÍTICO] {str(e)}")
            messagebox.showerror("Error", "Archivo inválido o formato incorrecto.")

    # ENCABEZADO Y NOTEBOOK PRINCIPAL
    header_frame = ttk.Frame(root, padding=15)
    header_frame.pack(fill='x')
    ttk.Label(header_frame, text="Simulador de Autómatas Finitos Deterministas y No Deterministas", style="Header.TLabel").pack()
    
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=20, pady=(0, 20))

    # --- PESTAÑA 1: DEFINICIÓN ---
    tab1 = tk.Frame(notebook, bg="#f0f2f5")
    notebook.add(tab1, text="Definición y Carga ")

    panel_izq = ttk.Frame(tab1)
    panel_izq.pack(side=tk.LEFT, fill='y', padx=15, pady=15)
    ttk.Button(panel_izq, text="🔍 Explorar Archivo", command=cargar_archivo).pack(fill='x', pady=(0, 15), ipady=5)

    frame_info = ttk.LabelFrame(panel_izq, text=" 5 Tuplas del Autómata ")
    frame_info.pack(fill='both', expand=True)
    ttk.Label(frame_info, text="Alfabeto:", font=("Segoe UI", 9, "italic")).pack(anchor='w', padx=10, pady=(10,0))
    lbl_alfabeto = ttk.Label(frame_info, text="Σ = { }", font=("Consolas", 12, "bold"), foreground="#2b6cb0")
    lbl_alfabeto.pack(anchor='w', padx=10)
    ttk.Label(frame_info, text="Estados:", font=("Segoe UI", 9, "italic")).pack(anchor='w', padx=10, pady=(10,0))
    lbl_estados = ttk.Label(frame_info, text="Q = { }", font=("Consolas", 11, "bold"), foreground="#2b6cb0")
    lbl_estados.pack(anchor='w', padx=10)
    ttk.Label(frame_info, text="Estado Inicial:", font=("Segoe UI", 9, "italic")).pack(anchor='w', padx=10, pady=(10,0))
    lbl_inicial = ttk.Label(frame_info, text="q0 = ", font=("Consolas", 12, "bold"), foreground="#38a169")
    lbl_inicial.pack(anchor='w', padx=10)
    ttk.Label(frame_info, text="Estados Finales:", font=("Segoe UI", 9, "italic")).pack(anchor='w', padx=10, pady=(10,0))
    lbl_finales = ttk.Label(frame_info, text="F = { }", font=("Consolas", 12, "bold"), foreground="#e53e3e")
    lbl_finales.pack(anchor='w', padx=10, pady=(0, 10))

    panel_der = ttk.Frame(tab1)
    panel_der.pack(side=tk.RIGHT, fill='both', expand=True, padx=15, pady=15)
    frame_tabla = ttk.LabelFrame(panel_der, text=" Función de Transición ")
    frame_tabla.pack(fill='both', expand=True, pady=(0, 10))
    tabla_transiciones = ttk.Treeview(frame_tabla, columns=("origen", "flecha", "destino"), show="headings")
    tabla_transiciones.heading("origen", text="Estado + Lectura")
    tabla_transiciones.heading("flecha", text="")
    tabla_transiciones.heading("destino", text="Destino")
    tabla_transiciones.column("origen", anchor='center', width=200)
    tabla_transiciones.column("flecha", anchor='center', width=50)
    tabla_transiciones.column("destino", anchor='center', width=150)
    scroll_tabla = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=tabla_transiciones.yview)
    tabla_transiciones.configure(yscroll=scroll_tabla.set)
    scroll_tabla.pack(side=tk.RIGHT, fill=tk.Y)
    tabla_transiciones.pack(fill='both', expand=True, padx=2, pady=2)
    tabla_transiciones.tag_configure('par', background='#f7fafc')
    tabla_transiciones.tag_configure('impar', background='#ffffff')

    frame_consola = ttk.LabelFrame(panel_der, text=" Consola ")
    frame_consola.pack(fill='x')
    consola = tk.Text(frame_consola, height=6, bg="#1a202c", fg="#48bb78", font=("Consolas", 10), state=tk.DISABLED)
    consola.pack(fill='both', expand=True, padx=2, pady=2)

    # --- PESTAÑA 2: SIMULACIÓN ---
    tab2 = tk.Frame(notebook, bg="#f0f2f5")
    notebook.add(tab2, text="Simulación Paso a Paso ")

    frame_entrada = ttk.Frame(tab2, padding=20)
    frame_entrada.pack(fill='x')
    ttk.Label(frame_entrada, text="Ingresa la cadena:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 10))
    entry_cadena = ttk.Entry(frame_entrada, font=("Consolas", 14), width=30)
    entry_cadena.pack(side=tk.LEFT, padx=10)
    
    def ejecutar_simulacion():
        if not app_state["motor"]:
            messagebox.showwarning("Alto", "Carga un autómata primero.")
            return
        cadena = entry_cadena.get()
        motor = app_state["motor"]
        for item in tabla_simulacion.get_children(): tabla_simulacion.delete(item)
            
        es_aceptada, historial = motor.simular_cadena_paso_a_paso(cadena)
        for paso in historial:
            estados_formateados = f"{{ {', '.join(paso['estados_activos'])} }}"
            tag = 'par' if paso['paso'] % 2 == 0 else 'impar'
            tabla_simulacion.insert("", tk.END, values=(paso['paso'], paso['simbolo'], estados_formateados), tags=(tag,))
            
        if es_aceptada: lbl_resultado.config(text="CADENA ACEPTADA", foreground="#38a169")
        else: lbl_resultado.config(text="CADENA RECHAZADA", foreground="#e53e3e")

    ttk.Button(frame_entrada, text="⚡ Ejecutar", command=ejecutar_simulacion).pack(side=tk.LEFT, padx=10, ipady=4)
    lbl_resultado = ttk.Label(tab2, text="ESPERANDO CADENA...", font=("Segoe UI", 20, "bold"), foreground="#718096")
    lbl_resultado.pack(pady=10)

    frame_recorrido = ttk.LabelFrame(tab2, text=" Trazabilidad de Ramificaciones (AFND) y Clausura λ ")
    frame_recorrido.pack(fill='both', expand=True, padx=20, pady=(0, 20))
    tabla_simulacion = ttk.Treeview(frame_recorrido, columns=("paso", "simbolo", "estados"), show="headings")
    tabla_simulacion.heading("paso", text="Paso")
    tabla_simulacion.heading("simbolo", text="Símbolo Leído")
    tabla_simulacion.heading("estados", text="Conjunto de Estados Activos")
    tabla_simulacion.column("paso", anchor='center', width=80)
    tabla_simulacion.column("simbolo", anchor='center', width=150)
    tabla_simulacion.column("estados", anchor='center', width=500)
    scroll_sim = ttk.Scrollbar(frame_recorrido, orient=tk.VERTICAL, command=tabla_simulacion.yview)
    tabla_simulacion.configure(yscroll=scroll_sim.set)
    scroll_sim.pack(side=tk.RIGHT, fill=tk.Y)
    tabla_simulacion.pack(fill='both', expand=True, padx=2, pady=2)
    tabla_simulacion.tag_configure('par', background='#f7fafc')
    tabla_simulacion.tag_configure('impar', background='#ffffff')

    # --- PESTAÑA 3: MINIMIZACIÓN LADO A LADO ---
    tab3 = tk.Frame(notebook, bg="#f0f2f5")
    notebook.add(tab3, text="Minimización y Reducción ")

    frame_controles_min = ttk.Frame(tab3, padding=15)
    frame_controles_min.pack(fill='x')

    def ejecutar_minimizacion():
        if not app_state["motor"]:
            messagebox.showwarning("Alto", "Carga un autómata primero.")
            return

        for item in tabla_orig.get_children(): tabla_orig.delete(item)
        for item in tabla_mini.get_children(): tabla_mini.delete(item)

        # 1. Llenar tabla original
        datos_orig = app_state["datos_json"]["transiciones"]
        for i, t in enumerate(datos_orig):
            tag = 'par' if i % 2 == 0 else 'impar'
            tabla_orig.insert("", tk.END, values=(t["de"], "→", t["a"]), tags=(tag,))

        # 2. Ejecutar Algoritmo
        resultado = app_state["motor"].minimizar_afd()

        # 3. Llenar tabla minimizada
        for i, t in enumerate(resultado["nuevas_transiciones"]):
            tag = 'par' if i % 2 == 0 else 'impar'
            tabla_mini.insert("", tk.END, values=(t["de"], f"--({t['lee']})-->", t["a"]), tags=(tag,))

        # 4. Mostrar Estadísticas
        estados_orig = len(app_state["motor"].transiciones)
        estados_nuevos = len(resultado["particiones"])
        eliminados = len(resultado["eliminados"])

        texto_stats = f"Estados Originales: {estados_orig} | Minimizados: {estados_nuevos} | Inalcanzables Eliminados: {eliminados}"
        lbl_stats_min.config(text=texto_stats)

        if estados_orig == estados_nuevos:
            messagebox.showinfo("Información", "El autómata ya está en su forma mínima. No hay estados equivalentes para fusionar.")
        else:
            grupos_fusionados = [f"Grupo Equivalente: {{{','.join(g)}}}" for g in resultado["particiones"] if len(g) > 1]
            msg = "Minimización completada. Se agruparon:\n\n" + "\n".join(grupos_fusionados)
            messagebox.showinfo("Minimización Exitosa", msg)

    ttk.Button(frame_controles_min, text="✂️ Ejecutar Algoritmo Hopcroft", command=ejecutar_minimizacion).pack(side=tk.LEFT, padx=10, ipady=4)
    lbl_stats_min = ttk.Label(frame_controles_min, text="Esperando ejecución...", font=("Segoe UI", 11, "bold"), foreground="#2b6cb0")
    lbl_stats_min.pack(side=tk.LEFT, padx=20)

    # Contenedor para las dos tablas (Lado a lado)
    frame_tablas_min = ttk.Frame(tab3, padding=10)
    frame_tablas_min.pack(fill='both', expand=True)

    # Tabla Original (Izquierda)
    frame_orig = ttk.LabelFrame(frame_tablas_min, text=" Grafo Original ")
    frame_orig.pack(side=tk.LEFT, fill='both', expand=True, padx=5)
    
    tabla_orig = ttk.Treeview(frame_orig, columns=("origen", "flecha", "destino"), show="headings")
    tabla_orig.heading("origen", text="Origen")
    tabla_orig.heading("flecha", text="")
    tabla_orig.heading("destino", text="Destino")
    tabla_orig.column("origen", anchor='center', width=100)
    tabla_orig.column("flecha", anchor='center', width=50)
    tabla_orig.column("destino", anchor='center', width=100)
    
    scroll_orig = ttk.Scrollbar(frame_orig, orient=tk.VERTICAL, command=tabla_orig.yview)
    tabla_orig.configure(yscroll=scroll_orig.set)
    scroll_orig.pack(side=tk.RIGHT, fill=tk.Y)
    tabla_orig.pack(fill='both', expand=True, padx=2, pady=2)
    tabla_orig.tag_configure('par', background='#f7fafc')
    tabla_orig.tag_configure('impar', background='#ffffff')

    # Tabla Minimizada (Derecha)
    frame_mini = ttk.LabelFrame(frame_tablas_min, text=" Grafo Minimizado ")
    frame_mini.pack(side=tk.RIGHT, fill='both', expand=True, padx=5)
    
    tabla_mini = ttk.Treeview(frame_mini, columns=("origen", "flecha", "destino"), show="headings")
    tabla_mini.heading("origen", text="Origen Fusionado")
    tabla_mini.heading("flecha", text="")
    tabla_mini.heading("destino", text="Destino Fusionado")
    tabla_mini.column("origen", anchor='center', width=150)
    tabla_mini.column("flecha", anchor='center', width=60)
    tabla_mini.column("destino", anchor='center', width=150)
    
    scroll_mini = ttk.Scrollbar(frame_mini, orient=tk.VERTICAL, command=tabla_mini.yview)
    tabla_mini.configure(yscroll=scroll_mini.set)
    scroll_mini.pack(side=tk.RIGHT, fill=tk.Y)
    tabla_mini.pack(fill='both', expand=True, padx=2, pady=2)
    tabla_mini.tag_configure('par', background='#ebf8ff') # Color ligeramente azul para diferenciarlo
    tabla_mini.tag_configure('impar', background='#ffffff')

    # ==========================================
    # PESTAÑA 4: CONVERSIÓN AFND -> AFD (SUBCONJUNTOS)
    # ==========================================
    tab4 = tk.Frame(notebook, bg="#f0f2f5")
    notebook.add(tab4, text="Conversión a AFD (Subconjuntos) ")

    frame_controles_conv = ttk.Frame(tab4, padding=15)
    frame_controles_conv.pack(fill='x')

    def formatear_estado(f_set):
        """ Convierte un frozenset a un string bonito como {q0, q1} """
        if not f_set: return "Ø"
        return f"{{ {', '.join(sorted(list(f_set)))} }}"

    def ejecutar_conversion():
        if not app_state["motor"]:
            messagebox.showwarning("Alto", "Carga un autómata primero.")
            return

        for item in tabla_nuevos_estados.get_children(): tabla_nuevos_estados.delete(item)
        for item in tabla_nuevas_trans.get_children(): tabla_nuevas_trans.delete(item)

        resultado = app_state["motor"].convertir_afnd_a_afd()

        # 1. Llenar tabla de Estados (Determinación de aceptación)
        for est in resultado["estados"]:
            es_inicial = "SÍ" if est == resultado["inicial"] else "No"
            es_final = "SÍ" if est in resultado["finales"] else "No"
            nombre = formatear_estado(est)
            
            tag = 'final' if es_final == "SÍ" else 'normal'
            tabla_nuevos_estados.insert("", tk.END, values=(nombre, es_inicial, es_final), tags=(tag,))

        # 2. Llenar tabla de Transiciones Resultantes
        for i, t in enumerate(resultado["transiciones"]):
            tag = 'par' if i % 2 == 0 else 'impar'
            origen = formatear_estado(t["de"])
            destino = formatear_estado(t["a"])
            tabla_nuevas_trans.insert("", tk.END, values=(origen, f"--({t['lee']})-->", destino), tags=(tag,))

        lbl_stats_conv.config(text=f"Proceso completado. Se generaron {len(resultado['estados'])} estados deterministas.")

    ttk.Button(frame_controles_conv, text="🔄 Ejecutar Algoritmo de Subconjuntos", command=ejecutar_conversion).pack(side=tk.LEFT, padx=10, ipady=4)
    lbl_stats_conv = ttk.Label(frame_controles_conv, text="Esperando ejecución...", font=("Segoe UI", 11, "bold"), foreground="#2b6cb0")
    lbl_stats_conv.pack(side=tk.LEFT, padx=20)

    # Contenedor para las tablas de resultados
    frame_tablas_conv = ttk.Frame(tab4, padding=10)
    frame_tablas_conv.pack(fill='both', expand=True)

    # Tabla de Estados
    frame_est_conv = ttk.LabelFrame(frame_tablas_conv, text=" Determinación de Estados AFD ")
    frame_est_conv.pack(side=tk.LEFT, fill='both', expand=True, padx=5)
    
    tabla_nuevos_estados = ttk.Treeview(frame_est_conv, columns=("nombre", "inicial", "final"), show="headings")
    tabla_nuevos_estados.heading("nombre", text="Nuevo Estado (Subconjunto)")
    tabla_nuevos_estados.heading("inicial", text="¿Es Inicial?")
    tabla_nuevos_estados.heading("final", text="¿Es de Aceptación?")
    tabla_nuevos_estados.column("nombre", anchor='center', width=180)
    tabla_nuevos_estados.column("inicial", anchor='center', width=80)
    tabla_nuevos_estados.column("final", anchor='center', width=120)
    
    scroll_est_conv = ttk.Scrollbar(frame_est_conv, orient=tk.VERTICAL, command=tabla_nuevos_estados.yview)
    tabla_nuevos_estados.configure(yscroll=scroll_est_conv.set)
    scroll_est_conv.pack(side=tk.RIGHT, fill=tk.Y)
    tabla_nuevos_estados.pack(fill='both', expand=True, padx=2, pady=2)
    
    tabla_nuevos_estados.tag_configure('normal', background='#ffffff')
    tabla_nuevos_estados.tag_configure('final', background='#e6ffed', foreground='#22543d') # Resalta los de aceptación

    # Tabla de Transiciones
    frame_trans_conv = ttk.LabelFrame(frame_tablas_conv, text=" Nueva Tabla de Transiciones AFD ")
    frame_trans_conv.pack(side=tk.RIGHT, fill='both', expand=True, padx=5)
    
    tabla_nuevas_trans = ttk.Treeview(frame_trans_conv, columns=("origen", "flecha", "destino"), show="headings")
    tabla_nuevas_trans.heading("origen", text="Estado Origen")
    tabla_nuevas_trans.heading("flecha", text="")
    tabla_nuevas_trans.heading("destino", text="Estado Destino")
    tabla_nuevas_trans.column("origen", anchor='center', width=150)
    tabla_nuevas_trans.column("flecha", anchor='center', width=60)
    tabla_nuevas_trans.column("destino", anchor='center', width=150)
    
    scroll_trans_conv = ttk.Scrollbar(frame_trans_conv, orient=tk.VERTICAL, command=tabla_nuevas_trans.yview)
    tabla_nuevas_trans.configure(yscroll=scroll_trans_conv.set)
    scroll_trans_conv.pack(side=tk.RIGHT, fill=tk.Y)
    tabla_nuevas_trans.pack(fill='both', expand=True, padx=2, pady=2)
    tabla_nuevas_trans.tag_configure('par', background='#f7fafc')
    tabla_nuevas_trans.tag_configure('impar', background='#ffffff')

    # ==========================================
    # PESTAÑA 5: PRUEBAS MÚLTIPLES (POR LOTES)
    # ==========================================
    tab5 = tk.Frame(notebook, bg="#f0f2f5")
    notebook.add(tab5, text=" Pruebas Múltiples ")

    frame_controles_lotes = ttk.Frame(tab5, padding=15)
    frame_controles_lotes.pack(fill='x')

    def cargar_y_probar_lote():
        if not app_state["motor"]:
            messagebox.showwarning("Alto", "Carga un autómata en la Pestaña 1 primero.")
            return

        ruta = filedialog.askopenfilename(
            title="Selecciona el archivo de cadenas (.txt)", 
            filetypes=[("Archivos de texto", "*.txt")]
        )
        if not ruta: return

        # Limpiar tabla previa
        for item in tabla_lotes.get_children(): tabla_lotes.delete(item)

        try:
            # Leer el archivo TXT
            with open(ruta, 'r', encoding='utf-8') as f:
                # Leemos línea por línea quitando espacios extra. Ignoramos líneas vacías.
                cadenas = [linea.strip() for linea in f if linea.strip()] 
            
            aceptadas = 0
            rechazadas = 0

            # Procesar cada cadena usando nuestro motor
            for i, cadena in enumerate(cadenas):
                # Pequeña validación por si escriben "lambda" en el txt para probar la cadena vacía
                cadena_a_probar = "" if cadena.lower() in ["lambda", "λ", "epsilon"] else cadena

                es_aceptada, _ = app_state["motor"].simular_cadena_paso_a_paso(cadena_a_probar)
                
                if es_aceptada:
                    aceptadas += 1
                    resultado_txt = "Aceptada"
                    tag = 'aceptada'
                else:
                    rechazadas += 1
                    resultado_txt = "Rechazada"
                    tag = 'rechazada'
                
                texto_mostrar = cadena if cadena_a_probar else "λ (Cadena Vacía)"
                tabla_lotes.insert("", tk.END, values=(i+1, texto_mostrar, resultado_txt), tags=(tag,))

            # Actualizar estadísticas y avisar
            lbl_stats_lotes.config(text=f"Total Evaluadas: {len(cadenas)} | Aceptadas: {aceptadas} | Rechazadas: {rechazadas}")
            messagebox.showinfo("Lote Finalizado", f"Se generó el informe para {len(cadenas)} cadenas exitosamente.")

        except Exception as e:
            messagebox.showerror("Error de Lectura", f"No se pudo procesar el archivo:\n{e}")

    ttk.Button(frame_controles_lotes, text="Cargar Archivo .TXT y Evaluar", command=cargar_y_probar_lote).pack(side=tk.LEFT, padx=10, ipady=4)
    lbl_stats_lotes = ttk.Label(frame_controles_lotes, text="Esperando archivo...", font=("Segoe UI", 11, "bold"), foreground="#2b6cb0")
    lbl_stats_lotes.pack(side=tk.LEFT, padx=20)

    # Tabla de Resultados del Informe
    frame_tabla_lotes = ttk.LabelFrame(tab5, text=" Informe de Evaluación por Lotes ")
    frame_tabla_lotes.pack(fill='both', expand=True, padx=20, pady=(0, 20))

    tabla_lotes = ttk.Treeview(frame_tabla_lotes, columns=("num", "cadena", "resultado"), show="headings")
    tabla_lotes.heading("num", text="#")
    tabla_lotes.heading("cadena", text="Cadena Evaluada")
    tabla_lotes.heading("resultado", text="Resultado Final")
    
    tabla_lotes.column("num", anchor='center', width=50)
    tabla_lotes.column("cadena", anchor='center', width=400)
    tabla_lotes.column("resultado", anchor='center', width=150)

    scroll_lotes = ttk.Scrollbar(frame_tabla_lotes, orient=tk.VERTICAL, command=tabla_lotes.yview)
    tabla_lotes.configure(yscroll=scroll_lotes.set)
    scroll_lotes.pack(side=tk.RIGHT, fill=tk.Y)
    tabla_lotes.pack(fill='both', expand=True, padx=2, pady=2)

    # Colores semánticos para el reporte
    tabla_lotes.tag_configure('aceptada', background='#e6ffed', foreground='#22543d')
    tabla_lotes.tag_configure('rechazada', background='#fff5f5', foreground='#9b2c2c')

    root.mainloop()

if __name__ == "__main__":
    main()
