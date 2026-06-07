"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { StatusBadge } from "@/components/StatusBadge";
import { listDocuments, type DocumentRecord } from "@/lib/api/documents";
import { formatDate, formatLabel } from "@/lib/format";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listDocuments()
      .then((response) => setDocuments(response.documents))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load documents"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <main className="main stack">
        <div className="toolbar">
          <div>
            <h1>Documents</h1>
            <p className="muted">Uploaded defenses and parser status</p>
          </div>
          <Link className="button-link" href="/documents/upload">
            Upload
          </Link>
        </div>
        {error ? <section className="panel error">{error}</section> : null}
        <section className="panel">
          {loading ? <div className="muted">Loading...</div> : null}
          {!loading && documents.length === 0 ? <div className="muted">No documents yet.</div> : null}
          {documents.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Parse</th>
                  <th>Uploaded</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((document) => (
                  <tr key={document.id}>
                    <td>
                      <strong>{document.title}</strong>
                      <div className="muted">{document.original_filename}</div>
                    </td>
                    <td>{formatLabel(document.manual_document_type ?? document.detected_document_type)}</td>
                    <td>
                      <StatusBadge status={document.parse_status} />
                      {document.parse_error ? <div className="error small">{document.parse_error}</div> : null}
                    </td>
                    <td>{formatDate(document.created_at)}</td>
                    <td>
                      <Link className="secondary-link" href={`/documents/${document.id}`}>
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </section>
      </main>
    </AppShell>
  );
}
