<script lang="ts">
  import { onMount } from "svelte";
  import "./app.css";

  // Comment interface for the comments, stores the id, the user's email (w)
  interface Comment {
    _id: string;
    user: string; // User's email (my experience is that the email is usually more important via experience in Auth0, etc.)
    username?: string; // Display name, not necessary, assuming that it's optional
    text: string; // The actual contents of the comment
    timestamp: string;
  }

  let articles: any[] = []; 

  let loading = false; // Are the articles loading
  let error = ""; 
  let comments: Record<string, Comment[]> = {}; // Dictionary where the article URL is the key and the value is a list of the comments associated with that article
  let newComments: Record<string, string> = {}; // Used for when a user is typing a new comment, key is article URL and value is the typed text (so far)
  let showCommentsFor: string | null = null;
  let user: any = null; // Which user is logged in (default assumes no one is logged in)
  let isModerator = false;

  // For Redaction
  let editingCommentId: string | null = null; // Comment ID (will use mongo document ID)
  let editingText: string = "";
  let formError = ""; //General error variable

  // Gets the info of the user that is logged in (as in if they exist and whether they're a mod)
  async function fetchUser() {
    try {
      const res = await fetch("/api/user");
      const data = await res.json();
      user = data.user || null;

      // Determine if user is a moderator (hard coded)
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

  // Gets all comments for a certain article using the URL
  async function fetchCommentsForArticle(url: string) {
    try {
      const res = await fetch(`/api/comments?url=${encodeURIComponent(url)}`); //Communicates to the backend
      const data = await res.json();
      comments[url] = data.comments || [];
    } catch (err) {
      console.error(`Failed to fetch comments for ${url}:`, err);
      comments[url] = [];
    }
  }

  // Submit a new comment
  async function submitComment(url: string) {
    if (!user) {
      formError = "You must be logged in to post comments."; // Disallows people who aren't logged in from commenting
      return;
    }

    const text = newComments[url];
    if (!text.trim()) return;

    try {
      const res = await fetch("/api/comments", {
        method: "POST", // POST is for uploading/adding data
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, text }),
      });
      const data = await res.json();

      if (data.success) {
        if (!comments[url]) comments[url] = [];
        comments[url].push(data.comment); // Adds the comment that was just made
        await fetchCommentsForArticle(url); // Refreshes (so that the new comment shows up right after its added instead of requiring a refresh)
        newComments[url] = "";
      } else {
        formError = "Failed to post comment.";
      }
    } catch (err) {
      console.error("Error submitting comment:", err);
      formError = "Error submitting comment.";
    }
  }

  // Deletes the comment. Method is POST because we're not really deleting it just overwriting it 
  async function deleteComment(commentId: string, articleUrl: string) {
    try {
      const res = await fetch(`/api/comments/delete/${commentId}`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.success) {
        await fetchCommentsForArticle(articleUrl); // Refreshes the comments (no refresh needed to see change)
      } else {
        formError = "Failed to delete comment";
      }
    } catch (err) {
      console.error("Error deleting comment:", err);
      formError = "Error deleting comment";
    }
  }

  // Starts the redaction
  function startRedaction(comment: Comment) {
    editingCommentId = comment._id;
    editingText = comment.text;
  }

  // Cancels the redaction
  function cancelRedaction() {
    editingCommentId = null;
    editingText = "";
  }

  // Submit the redaction (selected characters will be replaced in the backend)
  // Primary redaction function, reworked from previous code (which just redacted the whole thing, which isn't useful)
  async function submitRedaction(commentId: string, articleUrl: string) {

    const textarea = document.querySelector("textarea");

    // Gets the start and end of the text selection
    const selectionStart = textarea?.selectionStart;
    const selectionEnd = textarea?.selectionEnd;

    // Tells the user to select text if they haven't 
    if (!selectionStart || !selectionEnd || selectionStart === selectionEnd) {
      formError = "Please select text to redact.";
      return;
    }

    // Gets the selected text and replaces it with the full block
    const selected = editingText.substring(selectionStart, selectionEnd);
    const redacted =
      editingText.substring(0, selectionStart) +
      "█".repeat(selected.length) +
      editingText.substring(selectionEnd); 

    try {
      const res = await fetch(`/api/comments/${commentId}`, {
        method: "PATCH", // PATCH method is for updating part of a resource
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: redacted }),
      });
      const data = await res.json();

      if (data.success) {
        // Update the comment in the local state
        const comment = comments[articleUrl].find((c) => c._id === commentId);
        if (comment) comment.text = redacted;
        // Stops the redaction 
        cancelRedaction();
      } else {
        formError = "Failed to redact comment.";
      }
    } catch (err) {
      console.error("Redact error:", err);
    }
  }

// Removes the comments panel by removign the article URL

  function closeComments() {
    showCommentsFor = null;
  }

  // Sets the article URL to the one that was selected and gets the comments for it
  async function openComments(articleUrl: string) {
    showCommentsFor = articleUrl;
    if (!comments[articleUrl]) {
      await fetchCommentsForArticle(articleUrl);
    }
  }

  onMount(async () => {
    await fetchUser();

    try {
      const res = await fetch("/api/articles");
      const data = await res.json();

      if (data.articles?.length > 0) {
        articles = data.articles;
        await Promise.all(
          articles.map(async (article) => {
            // Preload article comments
            await fetchCommentsForArticle(article.url);
            newComments[article.url] = "";
          }),
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
      {#if formError}
      <div class="form-error">{formError}</div>
      {/if}
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

              {#if isModerator && comment.text !== "Comment was removed by a moderator"}
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
