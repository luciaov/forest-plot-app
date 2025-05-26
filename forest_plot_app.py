import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

# --- Configuración de la Página de Streamlit ---
st.set_page_config(
    page_title="Generador de Forest Plot Interactivo",
    layout="centered", # O "wide" para una interfaz más ancha
    initial_sidebar_state="expanded" # Puedes cambiar a "collapsed" si prefieres
)

st.title("📈 Generador de Forest Plot Interactivo")
st.markdown("Sube tus datos, personaliza el gráfico y genera un **Forest Plot interactivo** de forma sencilla.")

# --- Función para Generar el Forest Plot con Plotly ---
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
    # En este caso, simplemente invertimos el orden si vienen de un archivo.
    df_sorted = df.iloc[::-1].copy() # Invertir el DataFrame para que el primer estudio esté arriba

    y_labels = df_sorted['label'].tolist()

    # Añadir los puntos (valores centrales) y las barras de error
    fig.add_trace(go.Scatter(
        x=df_sorted['value'],
        y=y_labels,
        mode='markers',
        marker=dict(symbol='square', size=10, color=plot_colors['marker']),
        error_x=dict(
            type='data',
            symmetric=False,
            array=df_sorted['upper_ci'] - df_sorted['value'],
            arrayminus=df_sorted['value'] - df_sorted['lower_ci'],
            visible=True,
            color=plot_colors['ci_line'],
            thickness=2,
            width=5 # Ancho de las "tapas" del intervalo de confianza
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
            automargin=True # Asegura que las etiquetas del eje Y se muestren completamente
        ),
        hovermode="y unified", # Tooltip al pasar por encima de la fila completa
        margin=dict(l=100, r=120, t=80, b=50), # Márgenes para el texto y etiquetas
        plot_bgcolor='rgba(0,0,0,0)', # Fondo del área de plot transparente
        paper_bgcolor='rgba(0,0,0,0)', # Fondo del papel transparente
        xaxis=dict(showgrid=True, gridcolor='lightgray', zeroline=False),
        yaxis=dict(showgrid=False)
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

# --- Carga de Datos ---
st.sidebar.header("📂 Cargar Datos")
uploaded_file = st.sidebar.file_uploader(
    "**Sube un archivo CSV o Excel**",
    type=["csv", "xls", "xlsx"],
    help="El archivo debe contener las columnas: `label`, `value`, `lower_ci`, `upper_ci`."
)

data_df = pd.DataFrame() # Inicializar un DataFrame vacío

if uploaded_file is not None:
    try:
        # Leer el archivo según su extensión
        if uploaded_file.name.endswith('.csv'):
            data_df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            data_df = pd.read_excel(uploaded_file)

        # Validar y estandarizar nombres de columnas
        required_cols = {'label', 'value', 'lower_ci', 'upper_ci'}
        if not required_cols.issubset(data_df.columns):
            st.error(
                "❌ **Error en el archivo:** Las columnas requeridas ('label', 'value', 'lower_ci', 'upper_ci') no se encontraron. "
                "Por favor, renombra las columnas en tu archivo para que coincidan exactamente (¡sensible a mayúsculas y minúsculas!)."
            )
            data_df = pd.DataFrame() # Vaciar el DataFrame para no intentar graficar con datos incorrectos
        else:
            # Convertir columnas a numérico, forzando errores a NaN
            for col in ['value', 'lower_ci', 'upper_ci']:
                data_df[col] = pd.to_numeric(data_df[col], errors='coerce')
            
            # Eliminar filas con valores NaN en las columnas críticas
            initial_rows = len(data_df)
            data_df.dropna(subset=['value', 'lower_ci', 'upper_ci'], inplace=True)
            if len(data_df) < initial_rows:
                st.sidebar.warning(f"⚠️ Se eliminaron {initial_rows - len(data_df)} filas con valores no numéricos válidos en 'value', 'lower_ci' o 'upper_ci'.")
            
            if data_df.empty:
                st.error("Archivo cargado, pero **no contiene datos válidos** para generar el gráfico después de la limpieza.")
            else:
                st.sidebar.success("✅ Archivo cargado y procesado correctamente.")
                st.sidebar.dataframe(data_df.head()) # Mostrar las primeras filas como vista previa

    except Exception as e:
        st.error(f"❌ **Error al procesar el archivo:** {e}. Asegúrate de que el archivo no esté dañado y que el formato sea correcto.")
        data_df = pd.DataFrame() # Vaciar el DataFrame en caso de error grave
else:
    st.info("⬆️ Sube un archivo CSV o Excel desde la barra lateral izquierda para empezar.")

# --- Personalización del Gráfico ---
st.sidebar.header("🎨 Personalizar Gráfico")

# Opciones de personalización agrupadas en un "expander" para limpiar la UI
with st.sidebar.expander("Opciones Generales"):
    plot_title = st.text_input("Título del Gráfico:", "Forest Plot de tus Datos")
    ref_line_value = st.number_input(
        "Valor de la Línea de Referencia:",
        value=0.0,
        help="Ej: '0' para diferencias de medias, '1' para Odds Ratio/Riesgos Relativos. Esta línea destaca un 'no efecto'."
    )
    x_axis_label = st.text_input("Etiqueta del Eje X:", "Valor Estimado e Intervalo de Confianza")

with st.sidebar.expander("Colores del Gráfico"):
    marker_color = st.color_picker("Color de Puntos:", "#0000FF") # Azul
    ci_line_color = st.color_picker("Color de Barras CI:", "#808080") # Gris
    ref_line_color = st.color_picker("Color de Línea de Referencia:", "#FF0000") # Rojo

plot_colors = {
    'marker': marker_color,
    'ci_line': ci_line_color,
    'ref_line': ref_line_color
}

# --- Generar y Mostrar el Forest Plot ---
st.header("📊 Tu Forest Plot")

if not data_df.empty:
    try:
        # Generar el Forest Plot interactivo usando la función
        fig = generate_plotly_forest_plot(
            data_df,
            title=plot_title,
            ref_line_value=ref_line_value,
            x_axis_label=x_axis_label,
            plot_colors=plot_colors
        )
        
        # Mostrar el gráfico interactivo de Plotly en Streamlit
        st.plotly_chart(fig, use_container_width=True)

        # --- Exportar como Imagen ---
        st.subheader("⬇️ Exportar Gráfico")
        
        # Botón para descargar como PNG
        st.download_button(
            label="Descargar como PNG",
            data=fig.to_image(format="png", engine="kaleido", width=1200, height=700, scale=2), # scale=2 para mayor resolución
            file_name=f"{plot_title.replace(' ', '_')}_forest_plot.png",
            mime="image/png",
            help="Descarga el gráfico como una imagen PNG de alta resolución."
        )

        # Botón para descargar como SVG (vectorial)
        st.download_button(
            label="Descargar como SVG",
            data=fig.to_image(format="svg", engine="kaleido", width=1200, height=700, scale=2),
            file_name=f"{plot_title.replace(' ', '_')}_forest_plot.svg",
            mime="image/svg+xml",
            help="Descarga el gráfico como una imagen SVG vectorial, ideal para edición y escalado sin pérdida de calidad."
        )

    except Exception as e:
        st.error(f"❌ **Error al generar el gráfico:** Asegúrate de que los datos sean válidos (valores numéricos). Detalles: {e}")
else:
    st.info("Sube tus datos y configura las opciones en la barra lateral izquierda para generar el Forest Plot.")

st.markdown("---")
st.markdown("Creado con ❤️ por tu Asistente de IA")