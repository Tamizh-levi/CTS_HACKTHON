// Run once: mongosh setup_team_db.js
const teamDb = db.getSiblingDB("cts_incident_management");
teamDb.ticket_history.createIndex({ ticket_id: 1 }, { unique: true });
teamDb.ticket_history.createIndex({ status: 1 });
teamDb.ticket_history.createIndex({ severity: 1 });
teamDb.ticket_history.createIndex({ technician_id: 1 });

const now = new Date();
const daysAgo = n => new Date(Date.now() - n * 86400000);
const docs = [
  { ticket_id: "1855", location: "location 662", region: "region_2", resource_type: "resource_type 8", severity: 1, technician_id: "T002", part_status: "in_stock", status: "resolved", kb_entry_id: "kb_41", attempt_number: 0, source: "real_resolution", created_at: daysAgo(2), updated_at: daysAgo(2) },
  { ticket_id: "2210", location: "location 118", region: "region_8", resource_type: "resource_type 2", severity: 2, technician_id: "T011", part_status: "in_stock", status: "resolved", kb_entry_id: "kb_12", attempt_number: 1, source: "real_resolution", created_at: daysAgo(1), updated_at: daysAgo(1) },
  { ticket_id: "3305", location: "location 455", region: "region_5", resource_type: "resource_type 6", severity: 2, technician_id: "T015", part_status: "in_stock", status: "escalated", kb_entry_id: "kb_77", attempt_number: 2, source: "synthetic", created_at: daysAgo(1), updated_at: now },
  { ticket_id: "4410", location: "location 231", region: "region_1", resource_type: "resource_type 4", severity: 0, technician_id: "T007", part_status: "out_of_stock", status: "assigned", kb_entry_id: "kb_09", attempt_number: 0, source: "synthetic", created_at: now, updated_at: now },
  { ticket_id: "99001", location: "location 314", region: "region_4", resource_type: "resource_type 99", severity: 2, technician_id: null, part_status: "out_of_stock", status: "escalated", kb_entry_id: null, attempt_number: 0, source: "synthetic", created_at: now, updated_at: now }
];
teamDb.ticket_history.bulkWrite(docs.map(doc => ({ updateOne: { filter: { ticket_id: doc.ticket_id }, update: { $setOnInsert: doc }, upsert: true } })));

// Optional production read-only account (change the password):
// teamDb.createUser({user:"nlq_readonly", pwd:"replace-this-password", roles:[{role:"read", db:"cts_incident_management"}]});
