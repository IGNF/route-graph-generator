def getQueryByTableAndBoundingBox(table, bbox, columns=['*'], whereClauses=None):
    if whereClauses is None:
        whereClauses=['true']
    if bbox:
        whereClauses.append(
            'geom && ST_MakeEnvelope(%s)' % bbox
        )

    sql  = 'SELECT %s FROM %s ' %(','.join(columns), table)
    sql += 'WHERE ' + ' AND '.join(whereClauses)
    return sql
