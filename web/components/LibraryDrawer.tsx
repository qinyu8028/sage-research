"use client";

import { useEffect, useRef, useState } from "react";
import { listDocs, deleteDoc, uploadFile, type LibraryDoc } from "@/lib/api";

export default function LibraryDrawer() {
  const [docs, setDocs] = useState<LibraryDoc[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const [entering, setEntering] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listDocs()
      .then(setDocs)
      .finally(() => setLoading(false));
  }, []);

  // Click outside confirming row dismisses it
  useEffect(() => {
    if (!confirming) return;
    function handleClick(e: MouseEvent) {
      const target = e.target as HTMLElement;
      if (!target.closest("[data-confirm-row]")) {
        setConfirming(null);
      }
    }
    document.addEventListener("click", handleClick, true);
    return () => document.removeEventListener("click", handleClick, true);
  }, [confirming]);

  function handleDeleteClick(title: string) {
    setConfirming(title);
  }

  async function performDelete(title: string) {
    setDeleting(title);
    try {
      await deleteDoc(title);
      setConfirming(null);
      setRemoving(title);
      setTimeout(() => {
        setDocs((prev) => prev.filter((d) => d.title !== title));
        setRemoving(null);
      }, 300);
    } finally {
      setDeleting(null);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const result = await uploadFile(file);
        const key = result.title + "_" + Date.now();
        const newDoc: LibraryDoc = {
          title: result.title,
          source_type: "upload",
          added_at: new Date().toISOString(),
        };
        setEntering((prev) => new Set(prev).add(key));
        setDocs((prev) => [{ ...newDoc, _key: key } as LibraryDoc & { _key: string }, ...prev]);
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            setEntering((prev) => {
              const next = new Set(prev);
              next.delete(key);
              return next;
            });
          });
        });
      }
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  const hasContent = !loading && docs.length > 0;

  return (
    <>
      {/* Trigger button — fixed bottom-left, always visible */}
      <button
        onClick={() => setOpen(true)}
        className="fixed left-10 bottom-9 z-40 flex items-center gap-2 text-[13px] text-muted-foreground hover:text-foreground bg-surface/90 border border-foreground/10 rounded-xl px-3.5 py-2 shadow-sm hover:shadow transition-colors duration-200 active:scale-95 backdrop-blur-sm"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"
        >
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
        文献库
      </button>

      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-50 transition-colors duration-300 ${
          open ? "bg-foreground/4.5 pointer-events-auto" : "pointer-events-none"
        }`}
        onClick={() => { setOpen(false); setConfirming(null); }}
      />

      {/* Sidebar panel */}
      <div
        className={`fixed left-0 top-0 bottom-0 z-50 w-100 bg-surface border-r border-foreground/8 shadow-lg flex flex-col transition-transform duration-350 ease-[cubic-bezier(0.2,0.8,0.2,1)] ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <h2 className="text-[15px] font-medium text-foreground">
            文献库{hasContent && <span className="text-muted-foreground font-normal ml-1.5">· {docs.length}</span>}
          </h2>
          <button
            onClick={() => { setOpen(false); setConfirming(null); }}
            className="p-1 text-muted-foreground hover:text-foreground active:scale-80 transition-all duration-150"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Doc list */}
        <div ref={listRef} className="flex-1 overflow-y-auto px-3 thin-scroll">
          {loading && (
            <p className="text-[13px] text-muted-foreground px-2 py-4">加载中...</p>
          )}
          {!loading && docs.length === 0 && (
            <p className="text-[13px] text-muted-foreground px-2 py-4">暂无文献</p>
          )}
          {docs.map((doc) => {
            const key = (doc as LibraryDoc & { _key?: string })._key || doc.title;
            const isRemoving = removing === doc.title;
            const isEntering = entering.has(key);
            const isConfirming = confirming === doc.title;
            return (
              <div
                key={key}
                className="transition-all duration-300 ease-out"
                style={{
                  opacity: isRemoving || isEntering ? 0 : 1,
                  transform: isRemoving ? "translateX(-20px)" : isEntering ? "translateX(20px)" : "translateX(0)",
                  maxHeight: isRemoving ? 0 : 120,
                  overflow: "hidden",
                }}
              >
                <div
                  className="group relative px-2.5 py-2.5 rounded-lg hover:bg-background/60 transition-colors"
                  data-confirm-row={isConfirming ? "" : undefined}
                >
                  <p className="text-[14px] text-foreground/85 leading-snug break-words pr-6">{doc.title}</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {formatSourceType(doc.source_type)}
                    {" · "}
                    {new Date(doc.added_at).toLocaleDateString("zh-CN")}
                  </p>
                  <div className="absolute right-0 top-2 w-10 flex justify-center">
                    {/* Trash icon */}
                    <button
                      onClick={() => handleDeleteClick(doc.title)}
                      className={`p-1 text-muted-foreground hover:text-error active:scale-90 transition-opacity duration-150 ${
                        isConfirming ? "opacity-0 pointer-events-none" : "opacity-0 group-hover:opacity-100"
                      }`}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                        strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                        <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                    {/* Confirm group — overlays trash position */}
                    <div
                      className="absolute top-0 left-0 w-full flex flex-col items-center"
                      style={{
                        opacity: isConfirming ? 1 : 0,
                        pointerEvents: isConfirming ? "auto" : "none",
                        transition: "opacity 0.15s ease-out",
                      }}
                    >
                      <button
                        onClick={() => setConfirming(null)}
                        className="text-[11px] text-muted-foreground px-1.5 py-1 rounded hover:bg-foreground/5 active:scale-95"
                      >
                        取消
                      </button>
                      <button
                        onClick={() => performDelete(doc.title)}
                        disabled={deleting === doc.title}
                        className="text-[11px] text-error px-1.5 py-0.5 rounded hover:bg-error/10 active:scale-95"
                      >
                        {deleting === doc.title ? (
                          <span className="block w-3 h-3 mx-auto border border-current border-t-transparent rounded-full animate-spin" />
                        ) : "删除"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Upload area */}
        <div className="px-4 pb-4 pt-2 border-t border-foreground/6">
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-lg border border-dashed border-foreground/25 text-[13px] text-foreground/60 hover:text-foreground hover:border-foreground/40 hover:bg-background/50 active:scale-95 active:bg-background/80 transition-all duration-150"
          >
            {uploading ? (
              <>
                <span className="block w-3.5 h-3.5 border border-current border-t-transparent rounded-full animate-spin" />
                上传中...
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                  strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                </svg>
                上传文件
              </>
            )}
          </button>
          <input ref={fileRef} type="file" className="hidden" accept=".pdf,.md,.txt" multiple onChange={handleUpload} />
        </div>
      </div>
    </>
  );
}

function formatSourceType(type: string): string {
  switch (type) {
    case "arxiv": return "arXiv";
    case "upload": return "上传";
    case "report": return "研究报告";
    default: return type;
  }
}
