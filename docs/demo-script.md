# Lantern demo script

This walkthrough takes about two minutes and uses only the synthetic files in `demo/`.

1. Open `http://localhost:5173` with the API and local services running.
2. Upload `demo/honeybees.txt` and `demo/ocean-currents.txt`.
3. Select only `honeybees.txt` and ask: **How do bees communicate the distance to food?**
4. Expand the citation and show that the quoted sentence comes directly from the selected file.
5. Ask: **What causes deep ocean circulation?** The app should refuse because the ocean file is not selected.
6. Select `ocean-currents.txt`, ask the same question again, and expand its citation.

The story to emphasize is not merely that Lantern answers questions. Retrieval is scoped to the
user's selected documents, generation has an explicit abstention path, and application code
validates every citation ID and exact quote before returning it to the browser.
