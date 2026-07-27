import boto3

textract = boto3.client('textract')


def run_textract(image_path: str):
    with open(image_path, 'rb') as doc_file:
        doc_bytes = doc_file.read()
    response = textract.analyze_document(
        Document={'Bytes': doc_bytes},
        FeatureTypes=['FORMS', 'TABLES']
    )
    return response['Blocks']


def compute_ocr_quality(blocks):
    word_confidences = [b['Confidence'] for b in blocks if b['BlockType'] == 'WORD']
    if not word_confidences:
        return {'mean_confidence': 0, 'low_confidence_word_pct': 100, 'word_count': 0}
    mean_conf = sum(word_confidences) / len(word_confidences)
    low_conf_pct = (len([c for c in word_confidences if c < 50]) / len(word_confidences)) * 100
    return {
        'mean_confidence': round(mean_conf, 2),
        'low_confidence_word_pct': round(low_conf_pct, 2),
        'word_count': len(word_confidences)
    }


def should_route_to_human_review(quality: dict, mean_threshold=75, low_pct_threshold=25):
    if quality['mean_confidence'] < mean_threshold:
        return True, f"Mean OCR confidence {quality['mean_confidence']}% below threshold {mean_threshold}%"
    if quality['low_confidence_word_pct'] > low_pct_threshold:
        return True, f"{quality['low_confidence_word_pct']}% of words below 50% confidence"
    return False, "OCR quality acceptable for extraction"


def get_lines_with_position(blocks):
    lines = []
    for block in blocks:
        if block['BlockType'] == 'LINE':
            bbox = block['Geometry']['BoundingBox']
            lines.append({
                'text': block['Text'],
                'top': bbox['Top'],
                'left': bbox['Left'],
                'height': bbox['Height']
            })
    return lines