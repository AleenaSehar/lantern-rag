import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const document = {
  id: "doc-1",
  filename: "honeybees.txt",
  content_type: "text/plain",
  size_bytes: 262,
  status: "ready",
  chunk_count: 1,
  created_at: "2026-08-17T00:00:00Z",
  error: null,
  duplicate: false,
};

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  }));
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("grounded conversation", () => {
  it("reveals the exact source excerpt when a citation is expanded", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockImplementationOnce(() => jsonResponse({ documents: [document] }))
      .mockImplementationOnce(() => jsonResponse({
        query: "How do bees communicate distance?",
        status: "answered",
        answer: "The waggle dance duration communicates distance.",
        retrieved_chunk_count: 1,
        citations: [{
          chunk_id: "chunk-1",
          document_id: document.id,
          filename: document.filename,
          chunk_index: 0,
          page_number: null,
          char_start: 0,
          char_end: 262,
          quote: "its duration communicates distance",
        }],
      }));

    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(document.filename);
    await user.type(screen.getByLabelText("Question"), "How do bees communicate distance?");
    await user.click(screen.getByLabelText("Send question"));

    await screen.findByText("The waggle dance duration communicates distance.");
    await user.click(screen.getByRole("button", { name: /source 1: honeybees\.txt/i }));
    expect(screen.getByText("its duration communicates distance")).toBeVisible();
    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringContaining("/answers"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows insufficient evidence without rendering sources", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockImplementationOnce(() => jsonResponse({ documents: [document] }))
      .mockImplementationOnce(() => jsonResponse({
        query: "What is the capital of France?",
        status: "insufficient_evidence",
        answer: "The selected documents do not contain enough evidence to answer this question.",
        retrieved_chunk_count: 1,
        citations: [],
      }));

    const user = userEvent.setup();
    render(<App />);
    await screen.findByText(document.filename);
    await user.type(screen.getByLabelText("Question"), "What is the capital of France?");
    await user.click(screen.getByLabelText("Send question"));

    expect(await screen.findByText("Insufficient evidence")).toBeVisible();
    await waitFor(() => expect(screen.queryByText("Sources")).not.toBeInTheDocument());
  });
});
