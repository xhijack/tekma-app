import frappe

class ConditionBuilder:
    """
    SQL WHERE condition builder.

    Example
    -------
    builder = (
        ConditionBuilder()
        .where("i.is_stock_item = 1")
        .eq("i.disabled", 0)
        .in_("i.name", ["ITEM-001", "ITEM-002"])
        .warehouse("sle.warehouse", "Main Warehouse")
        .tree(
            "Item Group",
            "i.item_group",
            "Finished Goods",
            alias="ig",
        )
    )

    conditions, params = builder.build()
    """

    def __init__(self):
        self._conditions = []
        self._params = {}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_key(field):
        return (
            field.replace(".", "_")
            .replace("`", "")
            .replace(" ", "_")
            .lower()
        )

    def _add(self, condition=None, params=None):
        if condition:
            self._conditions.append(condition)

        if params:
            self._params.update(params)

        return self

    # ------------------------------------------------------------------
    # Basic
    # ------------------------------------------------------------------

    def where(self, sql):
        return self._add(sql)

    def raw(self, sql):
        return self._add(sql)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def eq(self, field, value, key=None):
        if value in (None, ""):
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} = %({key})s",
            {key: value},
        )

    def ne(self, field, value, key=None):
        if value in (None, ""):
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

    # ------------------------------------------------------------------
    # IN
    # ------------------------------------------------------------------

    def in_(self, field, values, key=None):
        if values in (None, "", [], (), set()):
            return self

        if not isinstance(values, (list, tuple, set)):
            values = [values]

        values = tuple(values)

        if not values:
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} IN %({key})s",
            {key: values},
        )

    def not_in(self, field, values, key=None):
        if values in (None, "", [], (), set()):
            return self

        if not isinstance(values, (list, tuple, set)):
            values = [values]

        values = tuple(values)

        if not values:
            return self

        key = key or self._normalize_key(field)

        return self._add(
            f"{field} NOT IN %({key})s",
            {key: values},
        )

    # ------------------------------------------------------------------
    # Between
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Tree
    # ------------------------------------------------------------------

    def tree(self, doctype, field, value, alias=None):
        if not value:
            return self

        nodes = frappe.db.get_values(
            doctype,
            value,
            ["lft", "rgt"],
            as_dict=True,
        )
        print(nodes, value)
        if not nodes:
            return self

        clauses = []
        
        alias = alias or self._normalize_key(doctype)
        for node in nodes:
            clauses.append(f"(t.lft >= {node.lft} AND t.rgt <= {node.rgt})")

        return self._add(
            f"""
            EXISTS (
                SELECT 1
                FROM `tab{doctype}` t
                WHERE (t.name = {field}
                  AND ({" OR ".join(clauses)}))
            )
            """,
            {}
        )

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    @property
    def conditions(self):
        return list(self._conditions)

    @property
    def params(self):
        return dict(self._params)

    def build(self):
        return (
            list(self._conditions),
            dict(self._params),
        )