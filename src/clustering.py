def detect_columns(lines, min_gap=0.08):
    if not lines:
        return [0.0, 1.0]
    left_positions = sorted(set(round(l['left'], 3) for l in lines))
    boundaries = [0.0]
    for i in range(1, len(left_positions)):
        gap = left_positions[i] - left_positions[i - 1]
        if gap >= min_gap:
            boundaries.append((left_positions[i] + left_positions[i - 1]) / 2)
    boundaries.append(1.0)
    return boundaries


def assign_to_columns(lines, boundaries):
    num_columns = len(boundaries) - 1
    columns = [[] for _ in range(num_columns)]
    for line in lines:
        for i in range(num_columns):
            if boundaries[i] <= line['left'] < boundaries[i + 1]:
                columns[i].append(line)
                break
    return [col for col in columns if col]


def cluster_lines_vertically(column_lines, gap_multiplier=1.5):
    if not column_lines:
        return []
    sorted_lines = sorted(column_lines, key=lambda x: x['top'])
    clusters = [[sorted_lines[0]]]
    for line in sorted_lines[1:]:
        prev = clusters[-1][-1]
        gap = line['top'] - (prev['top'] + prev['height'])
        if gap < prev['height'] * gap_multiplier:
            clusters[-1].append(line)
        else:
            clusters.append([line])
    return clusters


def cluster_document_dynamic(lines, min_gap=0.08, gap_multiplier=1.5):
    boundaries = detect_columns(lines, min_gap=min_gap)
    columns = assign_to_columns(lines, boundaries)
    result = {}
    for i, col in enumerate(columns):
        result[f'column_{i}_clusters'] = cluster_lines_vertically(col, gap_multiplier)
    return result, len(columns)