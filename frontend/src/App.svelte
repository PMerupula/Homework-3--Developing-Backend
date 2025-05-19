<script lang="ts">
  import { onMount } from "svelte";
  import "./app.css";
  
  // Mock article list (replace with real articles as needed)
  let articles: any[] = [
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
  
  let loading = false;
  let error = "";
  
  interface Comment {
    _id: string;
    user: string;
    text: string;
    timestamp: string;
    username?: string;
  }
  
  let comments: Record<string, Comment[]> = {};
  let newComments: Record<string, string> = {};
  let showCommentsFor: string | null = null;
  let user: any = null;
  
  let redactingCommentId: string | null = null;
  let redactSelection: Record<string, string> = {};
  let editingCommentId: string | null = null;
  let editingText: string = "";
  let isModerator = false;
  
  // Comment redaction: start editing
  function startRedaction(comment) {
    editingCommentId = comment._id;
    editingText = comment.text;
  }
  
  function cancelRedaction() {
    editingCommentId = null;
    editingText = "";
  }
  
  // Submit redaction with text replacement
  async function submitRedaction(commentId: string, articleUrl: string) {
    const textarea = document.querySelector("textarea");
    const selectionStart = textarea?.selectionStart;
    const selectionEnd = textarea?.selectionEnd;
  
    if (
      selectionStart == null ||
      selectionEnd == null ||
      selectionStart === selectionEnd
    ) {
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
        const target = comments[articleUrl].find((c) => c._id === commentId);
        if (target) target.text = redacted;
        cancelRedaction();
      } else {
        alert("Failed to redact comment.");
      }
    } catch (err) {
      console.error("Redact error:", err);
    }
  }
  
  // Fetch user info
  async function fetchUser() {
    try {
      const res = await fetch("/api/user");
      const data = await res.json();
      user = data.user || null;
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
  
  // Fetch comments for an article
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
  
  // Fetch all data on mount
  onMount(async () => {
    await fetchUser();
    try {
      const articleRes = await fetch("/api/articles");
      const articleData = await articleRes.json();
      if (articleData.articles?.length > 0) {
        articles = articleData.articles;
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
  
  // Open and close comment panel
  async function openComments(articleUrl: string) {
    showCommentsFor = articleUrl;
    if (!comments[articleUrl]) {
      await fetchCommentsForArticle(articleUrl);
    }
  }
  
  function closeComments() {
    showCommentsFor = null;
  }
  
  // Submit a comment
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
        comments[url].push(data.comment);
        await fetchCommentsForArticle(url);
        newComments[url] = "";
      } else {
        alert("Failed to post comment.");
      }
    } catch (err) {
      console.error("Error submitting comment:", err);
      alert("Error submitting comment.");
    }
  }
  
  // Delete a comment (set text to removed string)
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
  
  // Simple redact all logic
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
  </script>
  

<!-- 
  Contents below is pretty much just a direct copy-paste from my (Prince's) index.html file and the HTML contents from it. 
  Scripting will be in main.ts and styles in app.css.
  Nothing major was changed, apart from the removal of the pre-defined articles to make space for the articles that will be fetched from the New York Times API.
  -->
<main>
  <header>
    <!-- Not included in the figma, but I saw something similar on the actual New York Times website (granted on the website it was for the pages for the rest of the world), and thought it'd be neat to include a language option. -->
    <div class="language-bar">
      <nav class="language-nav">
        <button class="language-button">ENGLISH</button>
        <button class="language-button">ESPAÑOL</button>
        <button class="language-button">FRANÇAIS</button>
        <button class="language-button">中文</button>
      </nav>
      <div class="auth-nav">
        <!-- {#if user}
          <span class="user-email">{user.email}</span>
          <a href="http://localhost:8000/logout" class="auth-button">Logout</a>
        {:else}
          <a href="http://localhost:8000/login" class="auth-button">Login</a>
        {/if} -->
        {#if user}
          <span class="user-email">{user.email}</span>
          <a href="/logout" class="auth-button">Logout</a>
        {:else}
          <a href="/login" class="auth-button">Login</a>
        {/if}
      </div>
    </div>
    <!-- Title and Date-->
    <div class="middle-bar">
      <div class="left">
        <!-- "current-date" is used as the id. Placeholder text used as the script will dynamically set the date. -->
        <p id="current-date">[Insert date here]</p>
        <a
          href="https://www.nytimes.com/section/todayspaper"
          class="todays-paper">Today's Paper</a
        >
      </div>
      <!-- Font needs to be one that matches that of the front page. Handled in styles.css -->
      <h1 class="main-title">The New York Times</h1>

      <div id="stock-ticker" class="stock-ticker"></div>
    </div>

    <!-- Navigation Bar -->
    <nav class="main-nav">
      <a href="#">U.S. </a>
      <!-- <button type = "button" aria-label = "open The US sub">∨</button> -->
      <a href="#">World</a>
      <a href="#">Business</a>
      <a href="#">Arts</a>
      <a href="#">Lifestyle</a>
      <a href="#">Opinion</a>
      <a href="#">Audio</a>
      <a href="#">Games</a>
      <a href="#">Cooking</a>
      <a href="#">Wirecutter</a>
      <a href="#">The Athletic</a>
    </nav>
  </header>

  <div class="grid-container" id="articles-container">
    {#if loading}
      <p>Loading articles...</p>
    {:else if error}
      <p>{error}</p>
    {:else if articles.length === 0}
      <p>No articles found.</p>
    {:else}
      <!-- Display articles in grid -->
      {#each articles as article}
        <section class="column">
          <h2>{article.headline}</h2>
          <p>{article.abstract}</p>
          {#if article.image_url}
            <img
              src={article.image_url}
              alt={`Image for ${article.headline}`}
              class="article-image"
            />
          {/if}
          <p>
            <a href={article.url} target="_blank" rel="noopener noreferrer"
              >Read more</a
            >
          </p>
          <p>
            <small>
              {new Date(article.pub_date).toLocaleString("en-US", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </small>
          </p>
          <hr />

          <button
            class="comment-icon"
            on:click={() => openComments(article.url)}
          >
            💬
          </button>
        </section>
      {/each}
    {/if}
  </div>

  {#if showCommentsFor}
    <div class="comment-panel">
      <button class="close-btn" on:click={closeComments}>✖</button>
      <h3>Comments</h3>

      {#if comments[showCommentsFor]?.length}
        {#each comments[showCommentsFor] as comment}
          <div class="comment-item">
            <strong>{comment.username || comment.user}</strong>

            {#if editingCommentId === comment._id}
              <textarea bind:value={editingText} rows="3"></textarea>
              <button
                on:click={() => submitRedaction(comment._id, showCommentsFor!)}
                >Submit</button
              >
              <button on:click={cancelRedaction}>Cancel</button>
            {:else}
              <p>{comment.text}</p>
              <small>{comment.timestamp}</small>

              {#if isModerator && comment.text !== 'Comment was removed by a moderator'}
                <button on:click={() => startRedaction(comment)}>Redact</button>
                <button
                  on:click={() => deleteComment(comment._id, showCommentsFor!)}
                  >Delete</button
                >
              {/if}
            {/if}
          </div>
        {/each}
      {:else}
        <p>No comments yet.</p>
      {/if}

      <textarea
        bind:value={newComments[showCommentsFor]}
        rows="3"
        placeholder="Write your comment..."
      ></textarea>
      <button on:click={() => submitComment(showCommentsFor!)}
        >Post Comment</button
      >
    </div>
  {/if}

  <hr />
  <footer>
    <p>&copy; 2025 The New York Times (Prince and Ayden)</p>
  </footer>
</main>
