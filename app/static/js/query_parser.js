/**
 * query_parser.js – Client-side SQL query type detection.
 *
 * Mirrors the logic in app/services/query_parser_service.py so that the
 * frontend can determine the animation type without an extra round-trip.
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.QueryParser = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var TYPES = {
    SELECT : 'SELECT',
    INSERT : 'INSERT',
    UPDATE : 'UPDATE',
    DELETE : 'DELETE',
    CREATE : 'CREATE',
    ALTER  : 'ALTER',
    DROP   : 'DROP',
    OTHER  : 'OTHER'
  };

  /**
   * Strip SQL comments and return the first keyword.
   * @param  {string} sql
   * @return {string} One of the TYPES values.
   */
  function parseQueryType(sql) {
    if (!sql || !sql.trim()) return TYPES.OTHER;

    // Remove multi-line comments /* … */
    var cleaned = sql.replace(/\/\*[\s\S]*?\*\//g, ' ');
    // Remove single-line comments -- …
    cleaned = cleaned.replace(/--[^\n]*/g, ' ');
    cleaned = cleaned.trim();

    var firstToken = cleaned.split(/\s+/)[0].toUpperCase();

    var map = {
      'SELECT'  : TYPES.SELECT,
      'INSERT'  : TYPES.INSERT,
      'UPDATE'  : TYPES.UPDATE,
      'DELETE'  : TYPES.DELETE,
      'CREATE'  : TYPES.CREATE,
      'ALTER'   : TYPES.ALTER,
      'DROP'    : TYPES.DROP,
      'WITH'    : TYPES.SELECT,  // CTE
      'SHOW'    : TYPES.OTHER,
      'DESCRIBE': TYPES.OTHER,
      'DESC'    : TYPES.OTHER,
      'EXPLAIN' : TYPES.OTHER
    };

    return map[firstToken] || TYPES.OTHER;
  }

  return {
    parseQueryType: parseQueryType,
    TYPES: TYPES
  };
}));
