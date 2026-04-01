# Fix: Duplicate rows in `application_phase_materials` causing 500 errors

## Problem

The `POST /api/naka/{transport_code}/entry` endpoint crashes with a `500 Internal Server Error`:

```
sqlalchemy.exc.MultipleResultsFound: Multiple rows were found when one or none was required
```

**Root cause:** The `application_phase_materials` table contains duplicate `(application_id, phase, material_id)` rows. The `create_inspection_report` DAO method inserts phase materials with no duplicate check, so re-submitting an inspection report creates duplicate rows. There is also no database-level unique constraint to prevent this.

**Error location:** `backend/dao/application.py`, line 783 — `scalar_one_or_none()` in `create_naka_entry` expects 0 or 1 row but finds multiple.

---

## Changes Required

### 1. Fix `create_inspection_report` — add upsert logic

**File:** `backend/dao/application.py` (lines 723–733)

**Current code (broken):**
```python
if phase_materials:
    for pm in phase_materials:
        self.session.add(
            ApplicationPhaseMaterial(
                application_id=application_id,
                phase=pm.phase,
                material_id=pm.material_id,
                quantity=pm.quantity,
            )
        )
```

**Replace with (upsert pattern — same as `update_phase_materials` at lines 662–683):**
```python
if phase_materials:
    existing_stmt = select(ApplicationPhaseMaterial).where(
        ApplicationPhaseMaterial.application_id == application_id
    )
    existing_result = await self.session.execute(existing_stmt)
    existing_pm = {
        (pm.phase, pm.material_id): pm
        for pm in existing_result.scalars().all()
    }
    for pm in phase_materials:
        key = (pm.phase, pm.material_id)
        if key in existing_pm:
            existing_pm[key].quantity = pm.quantity
        else:
            self.session.add(
                ApplicationPhaseMaterial(
                    application_id=application_id,
                    phase=pm.phase,
                    material_id=pm.material_id,
                    quantity=pm.quantity,
                )
            )
```

---

### 2. Add `UniqueConstraint` to the SQLAlchemy model

**File:** `backend/dbmodels/application.py` (lines 206–228)

Add `__table_args__` to `ApplicationPhaseMaterial`:

```python
class ApplicationPhaseMaterial(Base):
    __tablename__ = "application_phase_materials"
    __table_args__ = (
        UniqueConstraint(
            "application_id", "phase", "material_id",
            name="uq_phase_material_per_application"
        ),
    )
    # ... rest of model unchanged
```

Also add `UniqueConstraint` to the imports from `sqlalchemy` at the top of the file.

---

### 3. Create Alembic migration

**New file:** `backend/migrations/versions/<generated_id>_add_unique_constraint_phase_materials.py`

- `down_revision = "cb5ecb4e393f"` (current HEAD migration)

**upgrade():**
1. Delete duplicate rows, keeping the one with the highest `id` per group:
   ```sql
   DELETE FROM application_phase_materials
   WHERE id NOT IN (
       SELECT MAX(id)
       FROM application_phase_materials
       GROUP BY application_id, phase, material_id
   );
   ```
2. Add the unique constraint:
   ```python
   op.create_unique_constraint(
       "uq_phase_material_per_application",
       "application_phase_materials",
       ["application_id", "phase", "material_id"],
   )
   ```

**downgrade():**
```python
op.drop_constraint(
    "uq_phase_material_per_application",
    "application_phase_materials",
    type_="unique",
)
```

---

### 4. Add duplicate guard to `ApplicationMaterialDAO`

**File:** `backend/dao/applicationmaterial.py` (lines 16–23)

Add a check-before-insert guard for the `(application_id, phase, material_id)` composite key, similar to the upsert pattern above.

---

## Verification Steps

1. Run `alembic upgrade head` to apply the migration (cleans up existing duplicates + adds constraint)
2. Test `POST /api/naka/{transport_code}/entry` — should no longer return 500
3. Test submitting an inspection report twice for the same application — should upsert quantities, not create duplicates
4. Test `GENERATE_TOKENS` workflow action — should still work correctly with the constraint in place
