from src.clustering import detect_columns, cluster_document_dynamic


def test_detect_columns_finds_single_gap():
    """Two clearly separated groups of lines should produce one internal
    boundary between them, splitting the page into two columns."""
    lines = [
        {'left': 0.05, 'top': 0.1},
        {'left': 0.06, 'top': 0.2},
        {'left': 0.55, 'top': 0.1},
        {'left': 0.56, 'top': 0.2},
    ]
    boundaries = detect_columns(lines, min_gap=0.08)
    # Expect 3 boundary points: start (0.0), the gap midpoint, and end (1.0)
    assert boundaries[0] == 0.0
    assert boundaries[-1] == 1.0
    assert len(boundaries) == 3


def test_detect_columns_no_gap_returns_single_column():
    """Lines with no significant horizontal gap should be treated as one
    column, not artificially split."""
    lines = [
        {'left': 0.10, 'top': 0.1},
        {'left': 0.12, 'top': 0.2},
        {'left': 0.11, 'top': 0.3},
    ]
    boundaries = detect_columns(lines, min_gap=0.08)
    assert len(boundaries) == 2  # just [0.0, 1.0] -- one column


def test_cluster_document_dynamic_groups_vertically_close_lines():
    """Lines close together vertically within the same column should be
    grouped into one cluster; a big vertical gap should start a new one."""
    lines = [
        {'text': 'Name: John', 'left': 0.05, 'top': 0.10, 'height': 0.02},
        {'text': 'Age: 40', 'left': 0.05, 'top': 0.12, 'height': 0.02},
        {'text': 'Unrelated section', 'left': 0.05, 'top': 0.50, 'height': 0.02},
    ]
    result, num_columns = cluster_document_dynamic(lines)
    assert num_columns == 1
    clusters = result['column_0_clusters']
    # Expect the first two lines grouped together, the far-away line separate
    assert len(clusters) == 2
    assert len(clusters[0]) == 2
    assert len(clusters[1]) == 1
