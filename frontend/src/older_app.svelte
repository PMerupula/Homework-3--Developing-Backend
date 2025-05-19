<script lang="ts">
    import { onMount } from "svelte";
    import "./app.css";
    
    // --------------------
    // TYPE DEFINITIONS
    // --------------------
    
    // Comment interface for each comment object
    interface Comment {
      _id: string;
      user: string;        // email of user (kept for backend compatibility)
      username?: string;   // optional display name (for showing on frontend)
      text: string;        // comment content
      timestamp: string;   // UTC timestamp
    }
    
    // --------------------
    // APPLICATION STATE
    // --------------------
    
    let articles: any[] = [
      // Placeholder mock articles (will be overwritten by real API data)
      {
        headline: "Mock Article 1",
        abstract: "This is a placeholder abstract for the first article...",
        url: "https://example.com/article1",
        pub_date: "2025-05-18T12:00:00Z",
        image_url: null,
      },
      {
        headline: "Mock Article 2",
        abstract: "Another placeholder to help visualize article layout.",
        url: "https://example.com/article2",
        pub_date: "2025-05-17T09:30:00Z",
        image_url: null,
      },
      {
        headline: "Mock Article 3",
        abstract: "Final mock entry before enabling the API again.",
        url: "https://example.com/article3",
        pub_date: "2025-05-16T07:45:00Z",
        image_url: null,
      },
    ];
    
    let loading = false;             // Whether articles are loading
    let error = "";                  // Error message to display
    let comments: Record<string, Comment[]> = {};  // Maps article URLs to their list of comments
    let newComments: Record<string, string> = {};  // Tracks new comment content per article
    let showCommentsFor: string | null = null;     // Currently visible comment panel
    let user: any = null;            // Logged-in user data from session
    let isModerator = false;         // Whether the user has mod privileges
    
    // Redaction UI state
    let editingCommentId: string | null = null;     // ID of comment being redacted
    let editingText: string = "";                   // Temp text for redaction
    
    // --------------------
    // USER & ROLE HELPERS
    // --------------------
    
    // Fetch logged-in user info from backend session
    async function fetchUser() {
      try {
        const res = await fetch("/api/user");
        const data = await res.json();
        user = data.user || null;
    
        // Determine if user is a moderator
        if (
          user?.email === "moderator@hw3.com" ||
          user?.email === "admin@hw3.com"
        ) {
          isModerator = true;
        }
      } catch (err) {
        console.error("Error fetching user:", err);
      }
    }
    
    // --------------------
    // COMMENT HANDLING
    // --------------------
    
    // Fetch all comments for a given article URL
    async function fetchCommentsForArticle(url: string) {
      try {
        const res = await fetch(`/api/comments?url=${encodeURIComponent(url)}`);
        const data = await res.json();
        comments[url] = data.comments || [];
      } catch (err) {
        console.error(`Failed to fetch comments for ${url}:`, err);
        comments[url] = [];
      }
    }
    
    // Submit a new comment to the backend
    async function submitComment(url: string) {
      if (!user) {
        alert("You must be logged in to post comments.");
        return;
      }
    
      const text = newComments[url];
      if (!text.trim()) return;
    
      try {
        const res = await fetch("/api/comments", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, text }),
        });
        const data = await res.json();
    
        if (data.success) {
          if (!comments[url]) comments[url] = [];
          comments[url].push(data.comment);  // Add the newly created comment
          await fetchCommentsForArticle(url); // Refresh the list
          newComments[url] = "";
        } else {
          alert("Failed to post comment.");
        }
      } catch (err) {
        console.error("Error submitting comment:", err);
        alert("Error submitting comment.");
      }
    }
    
    // Perform a soft delete (replace text with mod notice)
    async function deleteComment(commentId: string, articleUrl: string) {
      try {
        const res = await fetch(`/api/comments/delete/${commentId}`, {
          method: "POST",
        });
        const data = await res.json();
        if (data.success) {
          await fetchCommentsForArticle(articleUrl);
        } else {
          alert("Failed to delete comment");
        }
      } catch (err) {
        console.error("Error deleting comment:", err);
        alert("Error deleting comment");
      }
    }
    
    // Open redaction mode for a comment
    function startRedaction(comment: Comment) {
      editingCommentId = comment._id;
      editingText = comment.text;
    }
    
    // Cancel redaction UI
    function cancelRedaction() {
      editingCommentId = null;
      editingText = "";
    }
    
    // Submit redacted content to backend (partial redact)
    async function submitRedaction(commentId: string, articleUrl: string) {
      const textarea = document.querySelector("textarea");
      const selectionStart = textarea?.selectionStart;
      const selectionEnd = textarea?.selectionEnd;
    
      if (!selectionStart || !selectionEnd || selectionStart === selectionEnd) {
        alert("Please select text to redact.");
        return;
      }
    
      const selected = editingText.substring(selectionStart, selectionEnd);
      const redacted =
        editingText.substring(0, selectionStart) +
        "█".repeat(selected.length) +
        editingText.substring(selectionEnd);
    
      try {
        const res = await fetch(`/api/comments/${commentId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: redacted }),
        });
        const data = await res.json();
    
        if (data.success) {
          const comment = comments[articleUrl].find((c) => c._id === commentId);
          if (comment) comment.text = redacted;
          cancelRedaction();
        } else {
          alert("Failed to redact comment.");
        }
      } catch (err) {
        console.error("Redact error:", err);
      }
    }
    
    // Optional full-comment redact fallback
    async function redactComment(commentId: string, articleUrl: string) {
      try {
        const res = await fetch(`/api/comments/${commentId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ redact: true }),
        });
        const data = await res.json();
    
        if (data.success && comments[articleUrl]) {
          comments[articleUrl] = comments[articleUrl].map((c: Comment) =>
            c._id === commentId ? { ...c, text: "█".repeat(20) } : c
          );
        }
      } catch (err) {
        console.error("Failed to redact comment:", err);
      }
    }
    
    // --------------------
    // UI EVENT HANDLERS
    // --------------------
    
    function closeComments() {
      showCommentsFor = null;
    }
    
    async function openComments(articleUrl: string) {
      showCommentsFor = articleUrl;
      if (!comments[articleUrl]) {
        await fetchCommentsForArticle(articleUrl);
      }
    }
    
    // --------------------
    // APP LIFECYCLE INIT
    // --------------------
    
    onMount(async () => {
      await fetchUser();
    
      try {
        const res = await fetch("/api/articles");
        const data = await res.json();
    
        if (data.articles?.length > 0) {
          articles = data.articles;
          await Promise.all(
            articles.map(async (article) => {
              await fetchCommentsForArticle(article.url);
              newComments[article.url] = "";
            })
          );
        }
      } catch (err) {
        console.error("Error fetching articles or user:", err);
        error = "Failed to load articles.";
      } finally {
        loading = false;
      }
    });
    </script>
    