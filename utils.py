import math
import io
from PIL import Image


# Substitui valores inválidos ou não-serializáveis por valores aceitáveis em JSON.
def sanitize_movie_data(movie_data):
    for key, value in movie_data.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            movie_data[key] = None
        elif isinstance(value, list):
            movie_data[key] = [
                sanitize_movie_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, dict):
            movie_data[key] = sanitize_movie_data(value)
    return movie_data


def sanitize_filters(filters):
    """Sanitiza os filtros para garantir que valores $regex sejam strings"""
    if not isinstance(filters, dict):
        return {}
    
    sanitized = {}
    for key, value in filters.items():
        if key == "$or" and isinstance(value, list):
            # Processa lista de condições $or
            sanitized[key] = [sanitize_filters(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            # Processa operadores MongoDB como $regex
            sanitized_value = {}
            for op_key, op_value in value.items():
                if op_key == "$regex":
                    # Garante que $regex seja uma string
                    sanitized_value[op_key] = str(op_value) if op_value is not None else ""
                else:
                    sanitized_value[op_key] = op_value
            sanitized[key] = sanitized_value
        else:
            sanitized[key] = value
    
    return sanitized


def optimize_image(file_obj, max_width=800, quality=85):
    """
    Otimiza uma imagem redimensionando e comprimindo.
    
    Args:
        file_obj: Objeto de arquivo (FileStorage do Flask) ou BytesIO
        max_width: Largura máxima da imagem (padrão: 800px)
        quality: Qualidade JPEG de 1-100 (padrão: 85)
    
    Returns:
        BytesIO: Stream de bytes com a imagem otimizada
    
    Exemplo:
        Antes: 7.5 MB (2000x3000px)
        Depois: ~50-100 KB (800x1200px) - redução de ~98%
    """
    try:
        # Salva posição original do arquivo
        original_position = file_obj.tell() if hasattr(file_obj, 'tell') else 0
        file_obj.seek(0)
        
        # Lê tamanho original antes de processar
        file_obj.seek(0, 2)  # Vai para o fim
        original_size = file_obj.tell()
        file_obj.seek(0)  # Volta para o início
        
        # Lê a imagem original
        img = Image.open(file_obj)
        
        # Obtém formato original
        original_format = img.format or 'JPEG'
        
        # Redimensiona mantendo proporção (aspect ratio)
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Converte para RGB se necessário (para JPEG)
        save_format = original_format.upper() if original_format else 'JPEG'
        if save_format in ('JPEG', 'JPG'):
            if img.mode != 'RGB':
                img = img.convert('RGB')
        elif save_format == 'PNG' and img.mode not in ('RGBA', 'RGB', 'P'):
            img = img.convert('RGBA')
        
        # Cria buffer de saída
        output = io.BytesIO()
        
        # Salva imagem otimizada
        save_kwargs = {
            'format': save_format if save_format in ('PNG', 'JPEG', 'JPG') else 'JPEG',
            'optimize': True,
        }
        
        # Adiciona qualidade para JPEG
        if save_kwargs['format'] in ('JPEG', 'JPG'):
            save_kwargs['quality'] = quality
        
        img.save(output, **save_kwargs)
        
        # Volta para o início do buffer
        output.seek(0)
        
        # Log para debug (pode ser removido depois)
        new_size = len(output.getvalue())
        if original_size > 0:
            reduction = ((original_size - new_size) / original_size) * 100
            print(f"Imagem otimizada: {original_size / (1024*1024):.2f} MB -> {new_size / 1024:.2f} KB (redução de {reduction:.1f}%)")
        
        return output
        
    except Exception as e:
        print(f"Erro ao otimizar imagem: {e}")
        # Em caso de erro, retorna o arquivo original na posição original
        if hasattr(file_obj, 'seek'):
            file_obj.seek(original_position if 'original_position' in locals() else 0)
        return file_obj
