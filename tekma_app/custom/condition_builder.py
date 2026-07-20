import frappe


class ConditionBuilder:

    def __init__(self):
        self._conditions = []
        self._params = {}

    @staticmethod
    def _normalize_key(field):
        return (
            field.replace(".", "_")
            .replace("`", "")
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(",", "_")
            .lower()
        )

    @staticmethod
    def _normalize_values(values):
        if values is None or values == "":
            return []

        if isinstance(values, set):
            return list(values)

        if isinstance(values, (list, tuple)):
            return list(values)

        return [values]

    def _add(self, condition=None, params=None):
        if condition:
            self._conditions.append(condition.strip())

        if params:
            self._params.update(params)

        return self

    def where(self, sql):
        return self._add(sql)

    def raw(self, sql):
        return self._add(sql)

    def eq(self, field, value, key=None):
        if value is None or value == "":
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} = %({key})s",
            {key: value},
        )

    def ne(self, field, value, key=None):
        if value is None or value == "":
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} != %({key})s",
            {key: value},
        )

    def gt(self, field, value, key=None):
        if value is None:
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} > %({key})s",
            {key: value},
        )

    def gte(self, field, value, key=None):
        if value is None:
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} >= %({key})s",
            {key: value},
        )

    def lt(self, field, value, key=None):
        if value is None:
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} < %({key})s",
            {key: value},
        )

    def lte(self, field, value, key=None):
        if value is None:
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} <= %({key})s",
            {key: value},
        )

    def like(self, field, value, key=None):
        if not value:
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} LIKE %({key})s",
            {key: f"%{value}%"},
        )

    def in_(self, field, values, key=None):
        values = self._normalize_values(values)

        if not values:
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} IN %({key})s",
            {key: tuple(values)},
        )

    def not_in(self, field, values, key=None):
        values = self._normalize_values(values)

        if not values:
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} NOT IN %({key})s",
            {key: tuple(values)},
        )

    def between(self, field, start, end, key=None):
        if not start or not end:
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} BETWEEN %({key}_from)s AND %({key}_to)s",
            {
                f"{key}_from": start,
                f"{key}_to": end,
            },
        )

    def tree(self, doctype, field, values, alias=None):
        values = self._normalize_values(values)

        if not values:
            return self

        nodes = frappe.get_all(
            doctype,
            filters={
                "name": ["in", values],
            },
            fields=[
                "name",
                "lft",
                "rgt",
            ],
        )

        if not nodes:
            return self._add("1 = 0")

        alias = alias or self._normalize_key(doctype)

        clauses = []
        params = {}

        for index, node in enumerate(nodes):
            lft_key = f"{alias}_lft_{index}"
            rgt_key = f"{alias}_rgt_{index}"

            clauses.append(
                f"""
                (
                    t.lft >= %({lft_key})s
                    AND t.rgt <= %({rgt_key})s
                )
                """
            )

            params[lft_key] = node.lft
            params[rgt_key] = node.rgt

        return self._add(
            f"""
            EXISTS (
                SELECT 1
                FROM `tab{doctype}` t
                WHERE
                    t.name = {field}
                    AND (
                        {" OR ".join(clauses)}
                    )
            )
            """,
            params,
        )

    @property
    def conditions(self):
        return list(self._conditions)

    @property
    def params(self):
        return dict(self._params)

    def build(self):
        return self.conditions, self.params