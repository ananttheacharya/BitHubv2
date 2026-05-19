import React from 'react';
import anantImg from '../../ProfilePics/Anant/anant.jpeg';
import minishaImg from '../../ProfilePics/Minisha/minisha.jpeg';
import krishnaImg from '../../ProfilePics/Krishna/Krishna.jpeg';
import garimaImg from '../../ProfilePics/Garima/Garima.jpeg';

// Social Icon components (SVG)
const LinkedInIcon = () => (
  <svg className="creator-social-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '18px', height: '18px' }}>
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
    <rect x="2" y="9" width="4" height="12" />
    <circle cx="4" cy="4" r="2" />
  </svg>
);

const InstagramIcon = () => (
  <svg className="creator-social-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '18px', height: '18px' }}>
    <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" />
  </svg>
);

const GitHubIcon = () => (
  <svg className="creator-social-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '18px', height: '18px' }}>
    <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
  </svg>
);

const team = [
  {
    name: "Anant Acharya",
    role: "Lead Architect & Full-Stack Engineer",
    image: anantImg,
    socials: {
      linkedin: "https://www.linkedin.com/in/ananttheacharya/",
      instagram: "https://www.instagram.com/ananttheacharya/",
      github: "https://github.com/ananttheacharya"
    }
  },
  {
    name: "Minisha Singhal",
    role: "Front-End Engineer & Resource Curator",
    image: minishaImg,
    socials: {
      linkedin: "https://www.linkedin.com/in/minisha-singhal-863827372/",
      instagram: "https://www.instagram.com/minishasinghal/",
      github: "https://github.com/singhalminisha"
    }
  },
  {
    name: "Krishna Maheshwari",
    role: "Back-End Engineer",
    image: krishnaImg,
    socials: {
      linkedin: "https://www.linkedin.com/in/krishna-maheshwari-682b102a7/",
      instagram: "https://www.instagram.com/krishna249._/",
      github: "https://github.com/krishna-2506"
    }
  },
  {
    name: "Garima Sharma",
    role: "UI Designer",
    image: garimaImg,
    socials: {
      linkedin: "https://www.linkedin.com/in/garima-s-47422828a/",
      instagram: "https://www.instagram.com/garizzmaa/"
    }
  }
];

function CreatorsSection() {
  return (
    <section className="creators-section" id="creators-section">
      <div className="creators-section-header">
        <h2 className="creators-section-title">Meet the Creators</h2>
        <div className="creators-section-subtitle">The innovative team behind BitHub's design and intelligence</div>
      </div>
      <div className="creators-grid">
        {team.map((member, idx) => (
          <div className="creator-card" key={idx}>
            <div className="creator-card-inner">
              <div className="creator-image-wrapper">
                <img 
                  src={member.image} 
                  alt={member.name} 
                  className="creator-image"
                  loading="lazy"
                />
              </div>
              <h3 className="creator-name">{member.name}</h3>
              <p className="creator-role">{member.role}</p>
              <div className="creator-socials-row">
                {member.socials.linkedin && (
                  <a href={member.socials.linkedin} target="_blank" rel="noopener noreferrer" className="creator-social-link" title="LinkedIn">
                    <LinkedInIcon />
                  </a>
                )}
                {member.socials.instagram && (
                  <a href={member.socials.instagram} target="_blank" rel="noopener noreferrer" className="creator-social-link" title="Instagram">
                    <InstagramIcon />
                  </a>
                )}
                {member.socials.github && (
                  <a href={member.socials.github} target="_blank" rel="noopener noreferrer" className="creator-social-link" title="GitHub">
                    <GitHubIcon />
                  </a>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default CreatorsSection;
