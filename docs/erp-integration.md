# ERP Integration Architecture

The National Material Intelligence platform is designed to sit alongside legacy ERP systems (SAP, Oracle, Maximo) as a governance and intelligence layer, not a direct replacement for operational systems.

To avoid tight coupling to proprietary APIs, the platform uses the **Adapter Pattern** via the `MaterialSourceAdapter` interface.

## Supported Integration Patterns

### 1. SAP S/4HANA (OData)
For modern SAP systems, the recommended approach is integrating via OData APIs.
- **Protocol**: HTTP/REST
- **Capabilities**: CRUD operations on Material Masters, synchronous mapping updates.
- **Implementation**: Create an `ODataAdapter` inheriting from `MaterialSourceAdapter` utilizing `requests` or an OData client library.

### 2. SAP ECC (RFC/BAPI)
For legacy SAP ECC environments without NetWeaver Gateway enabled, use the official SAP NW RFC SDK.
- **Protocol**: RFC
- **Library**: `PyRFC`
- **Capabilities**: Direct execution of `BAPI_MATERIAL_GET_DETAIL` and `BAPI_MATERIAL_SAVEDATA`.
- **Implementation**: The `SAPAdapter` stub provided in `backend/app/adapters/sap_adapter.py` should be expanded to initialize a PyRFC connection pool.

### 3. Asynchronous Batch (IDoc / Flat File)
When real-time synchronization is not possible or desired due to load:
- **IDoc**: Forward MATMAS IDocs to a middleware (like SAP PI/PO), transforming them into REST API payloads accepted by the platform's `/api/v1/materials/upload` endpoint.
- **Flat File**: Nightly CSV dumps processed by the built-in `CSVAdapter`.

## Adapter Responsibilities
Every adapter must implement:
1. `fetch_materials()`: Used by the AI sync job to discover new materials.
2. `get_material()`: On-demand sync for a specific record.
3. `create_mapping()` & `update_mapping()`: Triggers when the Human-in-the-Loop approves a deduplication, allowing the ERP to be informed of the new standardized National Code.
4. `health_check()`: Displayed in the Admin Console.
