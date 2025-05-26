import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

# --- Configuración de la Página de Streamlit ---
st.set_page_config(
    page_title="Forest Plot Interactivo",
    layout="centered", # El gráfico se centra en la página
    initial_sidebar_state="collapsed" # La barra lateral empieza oculta
)

st.title("🌳 Generador de Forest Plot Interactivo")
st.markdown("Sube tus datos, ajusta las opciones y crea tu Forest Plot interactivo.")

# --- Sección de Carga de Datos ---
st.header("1. Sube tus Datos")
st.info("Tu archivo CSV o Excel debe tener estas 4 columnas exactamente:")
st.markdown("- `label` (texto: nombre del estudio/fila)")
st.markdown("- `value` (número: valor central estimado)")
st.markdown("- `lower_ci` (número: límite inferior del intervalo de confianza)")
st.markdown("- `upper_ci` (número: límite superior del intervalo de confianza)")

# Ejemplo de datos para copiar y pegar si no tienes un archivo
st.subheader("¿No tienes un archivo? Prueba con estos datos:")
st.code("""label,value,lower_ci,upper_ci
Estudio A,0.75,0.60,0.90
Estudio B,1.20,1.05,1.35
Estudio C,0.90,0.80,1.00
Estudio D,0.50,0.40,0.60
""")
st.markdown("Puedes copiar este texto, pegarlo en un Bloc de Notas (o editor de texto) y guardarlo como `ejemplo.csv`.")


uploaded_file = st.file_uploader(
    "Selecciona tu archivo CSV (.csv) o Excel (.xls, .xlsx):",
    type=["csv", "xls", "xlsx"]
)

data_df = pd.DataFrame() # DataFrame vacío por defecto

if uploaded_file is not None:
    try:
        # Leer el archivo
        if uploaded_file.name.endswith('.csv'):
            data_df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            data_df = pd.read_excel(uploaded_file)

        # Validar columnas
        required_cols = {'label', 'value', 'lower_ci', 'upper_ci'}
        if not required_cols.issubset(data_df.columns):
            st.error(
                "❌ **Error:** Faltan columnas. Asegúrate de tener `label`, `value`, `lower_ci`, `upper_ci`."
            )
            data_df = pd.DataFrame() # Vaciar si hay error
        else:
            # Convertir a numérico, forzando errores a NaN
            for col in ['value', 'lower_ci', 'upper_ci']:
                data_df[col] = pd.to_numeric(data_df[col], errors='coerce')
            
            # Eliminar filas con NaN en las columnas clave
            initial_rows = len(data_df)
            data_df.dropna(subset=['value', 'lower_ci', 'upper_ci'], inplace=True)
            if len(data_df) < initial_rows:
                st.warning(f"⚠️ Se eliminaron {initial_rows - len(data_df)} filas con datos no válidos.")
            
            if data_df.empty:
                st.error("El archivo no contiene datos válidos para el gráfico.")
            else:
                st.success("✅ Datos cargados correctamente. Primeras 5 filas:")
                st.dataframe(data_df.head())

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}. ¿Está dañado o es el formato correcto?")
        data_df = pd.DataFrame()

# --- Sección de Personalización del Gráfico ---
st.header("2. Personaliza tu Gráfico")

# Usamos columnas para una interfaz más limpia
col1, col2 = st.columns(2)

with col1:
    plot_title = st.text_input("Título del Gráfico:", "Mi Forest Plot")
    ref_line_value = st.number_input(
        "Línea de Referencia:",
        value=0.0,
        help="0 para diferencias (ej. 0.0), 1 para razones (ej. 1.0)."
    )

with col2:
    x_axis_label = st.text_input("Etiqueta del Eje X:", "Valor e Intervalo de Confianza")
    marker_color = st.color_picker("Color de Puntos:", "#0000FF") # Azul
    ci_line_color = st.color_picker("Color de Barras CI:", "#808080") # Gris
    ref_line_color = st.color_picker("Color de Línea Ref.:", "#FF0000") # Rojo

plot_colors = {
    'marker': marker_color,
    'ci_line': ci_line_color,
    'ref_line': ref_line_color
}

# --- Función para Generar el Forest Plot ---
def generate_plotly_forest_plot(df, title, ref_line_value, x_axis_label, plot_colors):
    """
    Genera un Forest Plot interactivo usando Plotly.

    Args:
        df (pd.DataFrame): DataFrame con las columnas 'label', 'value', 'lower_ci', 'upper_ci'.
        title (str): Título principal del gráfico.
        ref_line_value (float): Valor para la línea de referencia (ej. 0 o 1).
        x_axis_label (str): Etiqueta del eje X.
        plot_colors (dict): Diccionario con colores para 'marker', 'ci_line', 'ref_line'.

    Returns:
        plotly.graph_objects.Figure: Objeto figura de Plotly.
    """
    fig = go.Figure()

    # Ordenar los estudios para que aparezcan de abajo hacia arriba en el gráfico,
    # manteniendo el orden de entrada si no hay una columna de ordenación explícita.
    df_sorted = df.iloc[::-1].copy() # Invertir el DataFrame para que el primer estudio esté arriba

    y_labels = df_sorted['label'].tolist()

    # Añadir los puntos (valores centrales) y las barras de error
    fig.add_trace(go.Scatter(
        x=df_sorted['value'],
        y=y_labels,
        mode='markers',
        marker=dict(symbol='square', size=10, color=plot_colors['marker']),
        error_x=dict(
            type='data', symmetric=False,
            array=df_sorted['upper_ci'] - df_sorted['value'],
            arrayminus=df_sorted['value'] - df_sorted['lower_ci'],
            visible=True, color=plot_colors['ci_line'], thickness=2, width=5 # Ancho de las "tapas" del intervalo de confianza
        ),
        name='Estudio', # Nombre para el tooltip
        hoverinfo='x+y+text', # Mostrar valor, etiqueta y CI en el tooltip
        text=[f"CI: [{lc:.2f}, {uc:.2f}]" for lc, uc in zip(df_sorted['lower_ci'], df_sorted['upper_ci'])],
        showlegend=False
    ))

    # Añadir la línea de referencia vertical
    fig.add_vline(x=ref_line_value, line_width=1.5, line_dash="dash", line_color=plot_colors['ref_line'])

    # Personalizar el layout del gráfico
    fig.update_layout(
        title={
            'text': title,
            'y':0.95, # Posición del título
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title=x_axis_label,
        yaxis_title='', # Las etiquetas de los estudios son el eje Y
        yaxis=dict(
            categoryorder='array',
            categoryarray=y_labels,
            automargin=True, # Asegura que las etiquetas del eje Y se muestren completamente
            showgrid=False # Propiedad corregida: ahora está dentro del dict de yaxis
        ),
        hovermode="y unified", # Tooltip al pasar por encima de la fila completa
        margin=dict(l=100, r=120, t=80, b=50), # Márgenes para el texto y etiquetas
        plot_bgcolor='rgba(0,0,0,0)', # Fondo del área de plot transparente
        paper_bgcolor='rgba(0,0,0,0)', # Fondo del papel transparente
        xaxis=dict(showgrid=True, gridcolor='lightgray', zeroline=False)
    )

    # Añadir texto con los valores numéricos exactos al lado derecho del gráfico
    # Calculamos el rango del eje X para posicionar el texto de forma adaptativa
    x_min_data = df_sorted['lower_ci'].min()
    x_max_data = df_sorted['upper_ci'].max()
    
    # Considerar también el valor de la línea de referencia para el rango
    effective_min_x = min(x_min_data, ref_line_value)
    effective_max_x = max(x_max_data, ref_line_value)

    # Un factor de padding para dejar espacio para el texto y evitar que se salga del gráfico
    padding_factor = 0.20 # 20% del rango de los datos para el texto

    # Calcula el nuevo rango máximo del eje X para acomodar el texto
    calculated_x_range_max = effective_max_x + (effective_max_x - effective_min_x) * padding_factor
    calculated_x_range_min = effective_min_x - (effective_max_x - effective_min_x) * padding_factor * 0.1 # Pequeño padding a la izquierda

    fig.update_xaxes(range=[calculated_x_range_min, calculated_x_range_max])

    # Añadir las anotaciones de texto
    for i, row in df_sorted.iterrows():
        fig.add_annotation(
            x=calculated_x_range_max, # Posiciona el texto en el borde derecho del gráfico
            y=row['label'],
            text=f"{row['value']:.2f} [{row['lower_ci']:.2f}, {row['upper_ci']:.2f}]",
            showarrow=False,
            xanchor='right', # Alinea el texto a la derecha de la posición X
            yanchor='middle',
            font=dict(size=11, color='#555555')
        )
    return fig

# --- Sección de Visualización y Exportación ---
st.header("3. Tu Forest Plot y Exportación")

if not data_df.empty:
    try:
        # Generar el gráfico
        fig = generate_plotly_forest_plot(
            data_df,
            title=plot_title,
            ref_line_value=ref_line_value,
            x_axis_label=x_axis_label,
            plot_colors=plot_colors
        )
        
        # Mostrar el gráfico interactivo
        st.plotly_chart(fig, use_container_width=True)

        # Botones de descarga
        st.subheader("Descargar Gráfico")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="Descargar como PNG",
                data=fig.to_image(format="png", engine="kaleido", width=1200, height=700, scale=2), # scale=2 para mayor resolución
                file_name=f"{plot_title.replace(' ', '_')}_forest_plot.png",
                mime="image/png",
                help="Descarga el gráfico como una imagen PNG (para usar en presentaciones)."
            )
        with col_dl2:
            st.download_button(
                label="Descargar como SVG",
                data=fig.to_image(format="svg", engine="kaleido", width=1200, height=700, scale=2),
                file_name=f"{plot_title.replace(' ', '_')}_forest_plot.svg",
                mime="image/svg+xml",
                help="Descarga el gráfico como una imagen SVG (vectorial, ideal para edición profesional)."
            )

    except Exception as e:
        st.error(f"❌ **Error al generar el gráfico:** Revisa tus datos y opciones. Detalles: {e}")
else:
    st.info("Sube un archivo de datos en la sección 1 para ver tu Forest Plot aquí.")

st.markdown("---")
st.markdown("Hecho con ❤️ por tu Asistente de IA")
