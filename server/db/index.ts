import { createGetDb } from "@agent-native/core/db";
import { registerShareableResource } from "@agent-native/core/sharing";

import * as schema from "./schema.js";

export const getDb = createGetDb(schema);
export { schema };

// Cases can be shared with the other parent or guardian.
registerShareableResource({
  type: "case",
  resourceTable: schema.cases,
  sharesTable: schema.caseShares,
  displayName: "Case",
  titleColumn: "childAlias",
  getResourcePath: (row) => `/cases/${row.id}`,
  getDb,
});
