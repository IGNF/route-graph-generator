def getQueryByTableAndBoundingBox(table, bbox, columns=['*'], whereClauses=None):
    """
    Construit une requête SQL spatiale en fonction d'une BBOX au format string:
    xmin,ymin,xmax,ymax

    Parameters
    ----------
    table: str
    bbox: str
        'xmin,ymin,xmax,ymax'
    columns: [str]
        colonnes à selectionner
        par défaut toutes : ['*']
    whereClauses: [str]
        conditions qui ne sont pas liées à la bbox

    Returns
    -------
    dict
        configuration normalisée
    """
    if whereClauses is None:
        whereClauses=['true']
    if bbox:
        whereClauses.append(
            'geom && ST_MakeEnvelope(%s)' % bbox
        )

    sql  = 'SELECT %s FROM %s ' %(','.join(columns), table)
    sql += 'WHERE ' + ' AND '.join(whereClauses)
    sql += ' ORDER BY id ASC'
    return sql
