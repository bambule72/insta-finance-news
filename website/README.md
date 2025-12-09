# MemeCoin Marketing Website

A modern, responsive marketing website for the MemeCoin cryptocurrency project.

## Overview

This website serves as the primary marketing and information hub for MemeCoin, featuring:
- Hero section with animated elements
- About section explaining the project
- Tokenomics breakdown
- How-to-buy guides for both Ethereum and Solana
- Project roadmap
- Community links
- Responsive design for all devices

## Features

- **Modern Design**: Clean, gradient-based design with smooth animations
- **Responsive**: Works perfectly on desktop, tablet, and mobile devices
- **Fast Loading**: Minimal dependencies, optimized performance
- **Smooth Animations**: Intersection Observer for scroll animations
- **Interactive Elements**: Hover effects, smooth scrolling, particle effects
- **Multi-chain Support**: Instructions for both Ethereum and Solana

## Structure

```
website/
├── index.html           # Main HTML file
├── css/
│   └── style.css       # Stylesheet with all styling
├── js/
│   └── main.js         # JavaScript for interactivity
└── images/             # Images and assets (add your own)
```

## Local Development

### Option 1: Simple HTTP Server (Python)

```bash
cd website
python -m http.server 8000
```

Then open http://localhost:8000 in your browser.

### Option 2: Simple HTTP Server (Node.js)

```bash
# Install http-server globally
npm install -g http-server

# Run from website directory
cd website
http-server -p 8000
```

### Option 3: VS Code Live Server

1. Install "Live Server" extension in VS Code
2. Right-click on `index.html`
3. Select "Open with Live Server"

## Customization

### Update Contract Addresses

After deploying your smart contracts, update the contract addresses in `index.html`:

```html
<!-- Search for "Coming soon..." and replace with actual addresses -->
<code>0x1234...5678</code> <!-- Ethereum -->
<code>ABC...XYZ</code>      <!-- Solana -->
```

### Update Branding

1. **Colors**: Modify CSS variables in `css/style.css`:
```css
:root {
    --primary-color: #6c5ce7;
    --secondary-color: #fd79a8;
    --accent-color: #00b894;
}
```

2. **Logo/Icon**: Add your logo to `images/` and update in HTML
3. **Favicon**: Add favicon.ico to the website root

### Update Social Links

Replace placeholder `#` links with actual social media URLs:
- Twitter/X
- Telegram
- Discord
- Reddit

### Content Updates

Edit `index.html` to update:
- Token name and description
- Tokenomics percentages
- Roadmap items
- Team information
- Whitepaper links

## Deployment

### Option 1: GitHub Pages (Free)

1. Create a GitHub repository
2. Push website files to the repo
3. Go to Settings > Pages
4. Select branch and `/website` folder
5. Your site will be live at `https://username.github.io/repo-name/`

### Option 2: Netlify (Free)

1. Sign up at netlify.com
2. Connect your GitHub repository
3. Set build directory to `website`
4. Deploy automatically on every commit

### Option 3: Vercel (Free)

1. Sign up at vercel.com
2. Import your GitHub repository
3. Set root directory to `website`
4. Deploy with one click

### Option 4: Traditional Web Hosting

1. Upload all files from `website/` folder to your hosting
2. Ensure `index.html` is in the root directory
3. Configure your domain DNS settings

## SEO Optimization

### Add to index.html

```html
<!-- In <head> section -->
<meta name="keywords" content="memecoin, cryptocurrency, ethereum, solana, defi, token">
<meta property="og:title" content="MemeCoin - To The Moon">
<meta property="og:description" content="The next generation meme cryptocurrency">
<meta property="og:image" content="url-to-your-image">
<meta property="og:url" content="https://your-domain.com">
<meta name="twitter:card" content="summary_large_image">
```

### Create sitemap.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://your-domain.com/</loc>
    <lastmod>2024-01-01</lastmod>
    <priority>1.0</priority>
  </url>
</urlset>
```

### Create robots.txt

```
User-agent: *
Allow: /
Sitemap: https://your-domain.com/sitemap.xml
```

## Analytics

Add Google Analytics or other tracking:

```html
<!-- Add before </head> -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

## Performance Optimization

1. **Minify CSS/JS**: Use tools like UglifyJS or cssnano
2. **Optimize Images**: Use WebP format and compress images
3. **CDN**: Use a CDN for faster global delivery
4. **Caching**: Enable browser caching via headers
5. **Lazy Loading**: Add lazy loading for images

## Browser Support

The website supports:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Accessibility

- Semantic HTML5 elements
- Keyboard navigation support
- ARIA labels where needed
- Sufficient color contrast
- Responsive text sizing

## Additional Features to Add

Consider adding:
- **Live Price Chart**: Integrate DEX/CEX price data
- **Token Holder Counter**: Show number of holders
- **Burn Counter**: Display tokens burned
- **Newsletter Signup**: Email list for updates
- **Blog/News Section**: Latest updates
- **Team Section**: Meet the team
- **Whitepaper**: Downloadable PDF
- **Audit Reports**: Link to security audits

## Troubleshooting

### Fonts not loading
- Check Google Fonts CDN connection
- Use system fonts as fallback

### Animations not working
- Ensure JavaScript is enabled
- Check browser console for errors

### Mobile menu not working
- Verify JavaScript is loaded
- Check for CSS conflicts

## Resources

- [HTML5 Documentation](https://developer.mozilla.org/en-US/docs/Web/HTML)
- [CSS Documentation](https://developer.mozilla.org/en-US/docs/Web/CSS)
- [JavaScript Documentation](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
- [Web Accessibility](https://www.w3.org/WAI/)

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- Open an issue on GitHub
- Join our community Discord
- Check the FAQ section

---

Made with ❤️ by the MemeCoin community
