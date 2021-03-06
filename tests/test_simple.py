# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

from unittest import TestCase, skip

from moz_sql_parser import parse, sql_parser
from tests.util import assertRaises


class TestSimple(TestCase):

    def test_two_tables(self):
        result = parse("SELECT * from XYZZY, ABC")
        expected = {
            "select": "*",
            "from": ["XYZZY", "ABC"]
        }
        self.assertEqual(result, expected)

    def test_dot_table_name(self):
        result = parse("select * from SYS.XYZZY")
        expected = {
            "select": "*",
            "from": "SYS.XYZZY"
        }
        self.assertEqual(result, expected)

    def test_select_one_column(self):
        result = parse("Select A from dual")
        expected = {
            "select": {"value": "A"},
            "from": "dual"
        }
        self.assertEqual(result, expected)

    def test_select_quote(self):
        result = parse("Select '''' from dual")
        expected = {
            "select": {"value": {"literal": "'"}},
            "from": "dual"
        }
        self.assertEqual(result, expected)

    def test_select_quoted_name(self):
        result = parse('Select a "@*#&", b as test."g.g".c from dual')
        expected = {
            "select": [
                {"name": "@*#&", "value": "a"},
                {"name": "test.g.g.c", "value": "b"}
            ],
            "from": "dual"
        }
        self.assertEqual(result, expected)

    def test_select_expression(self):
        #                         1         2         3         4         5         6
        #               0123456789012345678901234567890123456789012345678901234567890123456789
        result = parse("SELECT a + b/2 + 45*c + (2/d) from dual")
        expected = {
            "select": {"value": {"add": [
                "a",
                {"div": ["b", 2]},
                {"mul": [45, "c"]},
                {"div": [2, "d"]}
            ]}},
            "from": "dual"
        }
        self.assertEqual(result, expected)

    def test_select_underscore_name(self):
        #                         1         2         3         4         5         6
        #               0123456789012345678901234567890123456789012345678901234567890123456789
        result = parse("select _id from dual")
        expected = {
            "select": {"value": "_id"},
            "from": "dual"
        }
        self.assertEqual(result, expected)

    def test_select_dots_names(self):
        #                         1         2         3         4         5         6
        #               0123456789012345678901234567890123456789012345678901234567890123456789
        result = parse("select a.b.c._d from dual")
        expected = {
            "select": {"value": "a.b.c._d"},
            "from": "dual"
        }
        self.assertEqual(result, expected)

    def test_select_many_column(self):
        result = parse("Select a, b, c from dual")
        expected = {
            "select": [
                {"value": "a"},
                {"value": "b"},
                {"value": "c"}
            ],
            "from": "dual"
        }
        self.assertEqual(result, expected)

    def test_bad_select1(self):
        assertRaises('Expected select', lambda: parse("se1ect A, B, C from dual"))

    def test_bad_select2(self):
        assertRaises('Expected {{expression1 [{[as] column_name1}]}', lambda: parse("Select &&& FROM dual"))

    def test_bad_from(self):
        assertRaises('(at char 20)', lambda: parse("select A, B, C frum dual"))

    def test_incomplete1(self):
        assertRaises('Expected {{expression1 [{[as] column_name1}]}', lambda: parse("SELECT"))

    def test_incomplete2(self):
        assertRaises("", lambda: parse("SELECT * FROM"))

    def test_where_neq(self):
        #                         1         2         3         4         5         6
        #               0123456789012345678901234567890123456789012345678901234567890123456789
        result = parse("SELECT * FROM dual WHERE a<>'test'")
        expected = {
            "select": "*",
            "from": "dual",
            "where": {"neq": ["a", {"literal": "test"}]}
        }
        self.assertEqual(result, expected)

    def test_where_in(self):
        result = parse("SELECT a FROM dual WHERE a in ('r', 'g', 'b')")
        expected = {
            "select": {"value": "a"},
            "from": "dual",
            "where": {"in": [
                "a",
                {"literal": ["r", "g", "b"]}
            ]}
        }
        self.assertEqual(result, expected)

    def test_where_in_and_in(self):
        #                         1         2         3         4         5         6
        #               0123456789012345678901234567890123456789012345678901234567890123456789
        result = parse("SELECT a FROM dual WHERE a in ('r', 'g', 'b') AND b in (10, 11, 12)")
        expected = {
            "select": {"value": "a"},
            "from": "dual",
            "where": {"and": [
                {"in": [
                    "a",
                    {"literal": ["r", "g", "b"]}
                ]},
                {"in": [
                    "b",
                    [10, 11, 12]
                ]}
            ]}
        }
        self.assertEqual(result, expected)

    def test_eq(self):
        result = parse("SELECT a, b FROM t1, t2 WHERE t1.a=t2.b")
        expected = {
            "select": [
                {"value": "a"},
                {"value": "b"}
            ],
            "from": ["t1", "t2"],
            "where": {"eq": ["t1.a", "t2.b"]}
        }
        self.assertEqual(result, expected)

    def test_is_null(self):
        result = parse("SELECT a, b FROM t1 WHERE t1.a IS NULL")
        expected = {
            "select": [
                {"value": "a"},
                {"value": "b"}
            ],
            "from": "t1",
            "where": {"missing": "t1.a"}
        }
        self.assertEqual(result, expected)

    def test_is_not_null(self):
        result = parse("SELECT a, b FROM t1 WHERE t1.a IS NOT NULL")
        expected = {
            "select": [
                {"value": "a"},
                {"value": "b"}
            ],
            "from": "t1",
            "where": {"exists": "t1.a"}
        }
        self.assertEqual(result, expected)

    def test_groupby(self):
        result = parse("select a, count(1) as b from mytable group by a")
        expected = {
            "select": [
                {"value": "a"},
                {"name": "b", "value": {"count": 1}}
            ],
            "from": "mytable",
            "groupby": {"value": "a"}
        }
        self.assertEqual(result, expected)

    def test_function(self):
        result = parse("select count(1) from mytable")
        expected = {
            "select": {"value": {"count": 1}},
            "from": "mytable"
        }
        self.assertEqual(result, expected)

    def test_order_by(self):
        result = parse("select count(1) from dual order by a")
        expected = {
            "select": {"value": {"count": 1}},
            "from": "dual",
            "orderby": {"value": "a"}
        }
        self.assertEqual(result, expected)

    def test_order_by_asc(self):
        result = parse("select count(1) from dual order by a asc")
        expected = {
            "select": {"value": {"count": 1}},
            "from": "dual",
            "orderby": {"value": "a", "sort": "asc"}
        }
        self.assertEqual(result, expected)

    def test_neg_or_precedence(self):
        result = parse("select B,C from table1 where A=-900 or B=100")
        expected = {
            'from': 'table1',
            'where': {'or': [{'eq': ['A', -900]}, {'eq': ['B', 100]}]},
            'select': [{'value': 'B'}, {'value': 'C'}]
        }
        self.assertEqual(result, expected)

    def test_negative_number(self):
        result = parse("select a from table1 where A=-900")
        expected = {
            'from': 'table1',
            'where': {'eq': ['A', -900]},
            'select': {'value': 'a'}
        }
        self.assertEqual(result, expected)

    def test_like_in_where(self):
        result = parse("select a from table1 where A like '%20%'")
        expected = {
            'from': 'table1',
            'where': {'like': ['A', {"literal": "%20%"}]},
            'select': {'value': 'a'}
        }
        self.assertEqual(result, expected)

    def test_not_like_in_where(self):
        result = parse("select a from table1 where A not like '%20%'")
        expected = {
            'from': 'table1',
            'where': {'nlike': ['A', {"literal": "%20%"}]},
            'select': {'value': 'a'}
        }
        self.assertEqual(result, expected)

    def test_like_in_select(self):
        result = parse("select case when A like 'bb%' then 1 else 0 end as bb from table1")
        expected = {
            'from': 'table1',
            'select': {'name': 'bb', 'value': {"case": [{"when": {"like": ["A", {"literal": "bb%"}]}, "then": 1}, 0]}}
        }
        self.assertEqual(result, expected)

    def test_not_like_in_select(self):
        result = parse("select case when A not like 'bb%' then 1 else 0 end as bb from table1")
        expected = {
            'from': 'table1',
            'select': {'name': 'bb', 'value': {"case": [{"when": {"nlike": ["A", {"literal": "bb%"}]}, "then": 1}, 0]}}
        }
        self.assertEqual(result, expected)

    def test_like_from_pr16(self):
        result = parse("select * from trade where school LIKE '%shool' and name='abc' and id IN ('1','2')")
        expected = {
            'from': 'trade',
            'where': {"and": [
                {"like": ["school", {"literal": "%shool"}]},
                {"eq": ["name", {"literal": "abc"}]},
                {"in": ["id", {"literal": ["1", "2"]}]}
            ]},
            'select': "*"
        }
        self.assertEqual(result, expected)

    def test_in_expression(self):
        result = parse("select * from task where repo.branch.name in ('try', 'mozilla-central')")
        expected = {
            'from': 'task',
            'select': "*",
            "where": {"in": [
                "repo.branch.name",
                {"literal": ["try", "mozilla-central"]}
            ]}
        }
        self.assertEqual(result, expected)

    def test_not_in_expression(self):
        result = parse("select * from task where repo.branch.name not in ('try', 'mozilla-central')")
        expected = {
            'from': 'task',
            'select': "*",
            "where": {"nin": [
                "repo.branch.name",
                {"literal": ["try", "mozilla-central"]}
            ]}
        }
        self.assertEqual(result, expected)

    def test_joined_table_name(self):
        result = parse("SELECT * FROM table1 t1 JOIN table3 t3 ON t1.id = t3.id")

        expected = {
            'from': [
                {'name': 't1', 'value': 'table1'},
                {'on': {'eq': ['t1.id', 't3.id']}, 'join': {'name': 't3', 'value': 'table3'}}
            ],
            'select': '*'
        }
        self.assertEqual(result, expected)

    @skip("hits stackdepth limit while parsing; too many KNOWN_OPS")
    def test_not_equal(self):
        #               0         1         2         3         4         5         6        7          8
        #               012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789
        result = parse("select * from task where build.product is not null and build.product!='firefox'")

        expected = {
            'select': '*',
            'from': "task",
            "where": {"and": [
                {"exists": "build.product"},
                {"neq": {"build.product": "firefox"}}
            ]}
        }
        self.assertEqual(result, expected)


    def test_pr19(self):
        result = parse("select empid from emp where ename like 's%' ")
        expected = {
            'from': 'emp',
            'where': {"like": ["ename", {"literal": "s%"}]},
            'select': {"value": "empid"}
        }
        self.assertEqual(result, expected)

    def test_backtick(self):
        result = parse("SELECT `user ID` FROM a")
        expected = {'select': {'value': 'user ID'}, 'from': 'a'}
        self.assertEqual(result, expected)

    def test_backtick_escape(self):
        result = parse("SELECT `user`` ID` FROM a")
        expected = {'select': {'value': 'user` ID'}, 'from': 'a'}
        self.assertEqual(result, expected)

    def test_left_join(self):
        result = parse("SELECT t1.field1 FROM t1 LEFT JOIN t2 ON t1.id = t2.id")
        expected = {'select': {'value': 't1.field1'},
                    'from': ['t1',
                    {'left join': 't2', 'on': {'eq': ['t1.id', 't2.id']}}]}
        self.assertEqual(result, expected)

    def test_multiple_left_join(self):
        result = parse("SELECT t1.field1 "
                       "FROM t1 "
                       "LEFT JOIN t2 ON t1.id = t2.id "
                       "LEFT JOIN t3 ON t1.id = t3.id"
                       )
        expected = {'select': {'value': 't1.field1'},
                    'from': ['t1',
                    {'left join': 't2', 'on': {'eq': ['t1.id', 't2.id']}},
                    {'left join': 't3', 'on': {'eq': ['t1.id', 't3.id']}}
                            ]}
        self.assertEqual(result, expected)

    def test_union(self):
        result = parse("SELECT b FROM t6 UNION SELECT '3' AS x ORDER BY x")
        expected = {
            "from": {'union': [
                {'from': 't6', 'select': {'value': 'b'}},
                {'select': {'value': {'literal': '3'}, 'name': 'x'}}
            ]},
            'orderby': {"value": 'x'}
        }
        self.assertEqual(result, expected)

    def test_left_outer_join(self):
        result = parse("SELECT t1.field1 FROM t1 LEFT OUTER JOIN t2 ON t1.id = t2.id")
        expected = {'select': {'value': 't1.field1'},
                    'from': ['t1',
                    {'left outer join': 't2', 'on': {'eq': ['t1.id', 't2.id']}}]}
        self.assertEqual(result, expected)

    def test_right_join(self):
        result = parse("SELECT t1.field1 FROM t1 RIGHT JOIN t2 ON t1.id = t2.id")
        expected = {'select': {'value': 't1.field1'},
                    'from': ['t1',
                    {'right join': 't2', 'on': {'eq': ['t1.id', 't2.id']}}]}
        self.assertEqual(result, expected)

    def test_right_outer_join(self):
        result = parse("SELECT t1.field1 FROM t1 RIGHT OUTER JOIN t2 ON t1.id = t2.id")
        expected = {'select': {'value': 't1.field1'},
                    'from': ['t1',
                    {'right outer join': 't2', 'on': {'eq': ['t1.id', 't2.id']}}]}
        self.assertEqual(result, expected)

    def test_full_join(self):
        result = parse("SELECT t1.field1 FROM t1 FULL JOIN t2 ON t1.id = t2.id")
        expected = {'select': {'value': 't1.field1'},
                    'from': ['t1',
                    {'full join': 't2', 'on': {'eq': ['t1.id', 't2.id']}}]}
        self.assertEqual(result, expected)

    def test_full_outer_join(self):
        result = parse("SELECT t1.field1 FROM t1 FULL OUTER JOIN t2 ON t1.id = t2.id")
        expected = {'select': {'value': 't1.field1'},
                    'from': ['t1',
                    {'full outer join': 't2', 'on': {'eq': ['t1.id', 't2.id']}}]}
        self.assertEqual(result, expected)

    def test_join_via_using(self):
        result = parse("SELECT t1.field1 FROM t1 JOIN t2 USING (id)")
        expected = {'select': {'value': 't1.field1'},
                    'from': ['t1',
                    {'join': 't2', 'using': 'id'}]}
        self.assertEqual(result, expected)

    def test_where_between(self):
        result = parse("SELECT a FROM dual WHERE a BETWEEN 1 and 2")
        expected = {
            "select": {"value": "a"},
            "from": "dual",
            "where": {"between": ["a", 1, 2]}
        }
        self.assertEqual(result, expected)

    def test_where_not_between(self):
        result = parse("SELECT a FROM dual WHERE a NOT BETWEEN 1 and 2")
        expected = {
            "select": {"value": "a"},
            "from": "dual",
            "where": {"not between": ["a", 1, 2]}
        }
        self.assertEqual(result, expected)
