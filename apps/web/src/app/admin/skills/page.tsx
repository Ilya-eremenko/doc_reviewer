"use client";

import { useEffect, useState } from "react";

import { AdminTabs } from "@/components/AdminTabs";
import { AppShell } from "@/components/AppShell";
import { listAdminSkills } from "@/lib/api/admin";
import type { SkillRecord } from "@/lib/api/skills";
import { formatLabel } from "@/lib/format";

export default function AdminSkillsPage() {
  const [skills, setSkills] = useState<SkillRecord[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listAdminSkills()
      .then((response) => setSkills(response.skills))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load admin skills"));
  }, []);

  return (
    <AppShell>
      <main className="main stack">
        <AdminTabs />
        <h1>Admin Skills</h1>
        {error ? <div className="error">{error}</div> : null}
        <section className="panel table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Version</th>
                <th>Status</th>
                <th>Schema</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {skills.map((item) => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td>{formatLabel(item.skill_type)}</td>
                  <td>{item.version}</td>
                  <td>{formatLabel(item.status)}</td>
                  <td>{item.result_schema_path}</td>
                  <td className="small">{item.source_snapshot.source_fingerprint ?? item.source_snapshot.source_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </AppShell>
  );
}
