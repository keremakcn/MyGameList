const {chromium}=require(process.env.PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.EDGE_PATH});
 const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const go=path=>page.goto('http://127.0.0.1:5064'+path);
 let checks=0;
 for(const lang of ['en','tr']){
  await go('/set-language/'+lang);
  for(const width of [320,360,390,412,640,844]){
   await page.setViewportSize({width,height:844});
   for(const path of ['/','/settings','/search','/search?q=Portal','/search?q=offline','/search?q=nothing','/search?q=Valve&type=developers','/search?q=Valve&type=publishers','/game/123','/game/124','/edit/125']){
    assert.equal((await go(path)).status(),200);
    const overflow=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,
     offenders:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>e.tagName+'.'+e.className).slice(0,8)}));
    assert(overflow.scroll<=width+1,`${lang} ${width} ${path}: ${JSON.stringify(overflow)}`);checks++;
   }
  }
 }
 await go('/set-language/en');await page.setViewportSize({width:390,height:844});
 await go('/search?q=Portal');
 const card=page.locator('.game-card').filter({has:page.getByRole('heading',{name:'Portal',exact:true})});
 await card.getByRole('button',{name:'+ Add to Want to Play',exact:true}).tap();
 await card.getByRole('button',{name:'✓ In your library',exact:true}).waitFor();
 assert(await card.getByRole('button',{name:'✓ In your library',exact:true}).isDisabled());
 assert.match(page.url(),/search\?q=Portal$/);
 await go('/edit/123');
 await page.locator('[name=status]').selectOption('Played');
 await page.locator('[name=my_rating]').fill('9');
 await page.locator('[name=note]').fill('Telefon notu. Kişisel yorum 🕹️. '+ 'Long private note. '.repeat(15));
 await page.locator('[name=favorite]').check();
 await page.locator('[name=played_date]').fill('2026-10-05');
 await Promise.all([page.waitForNavigation(),page.getByRole('button',{name:'Save',exact:true}).tap()]);
 await page.screenshot({path:'.qa/android-library-en.png',fullPage:true});
 const libraryCard=page.locator('#library-grid .game-card').filter({has:page.getByRole('heading',{name:'Portal',exact:true})});
 const firstTitle=await page.locator('#library-grid h3').first().textContent();
 await Promise.all([page.waitForNavigation(),libraryCard.locator('.delete-form button').tap()]);
 assert.equal(await page.locator('#library-grid h3').filter({hasText:'Portal'}).count(),0);
 await Promise.all([page.waitForNavigation(),page.getByRole('button',{name:'Undo',exact:true}).tap()]);
 assert.equal(await page.locator('#library-grid h3').first().textContent(),firstTitle);
 await go('/edit/123');
 assert.match(await page.locator('[name=note]').inputValue(),/Kişisel yorum/);
 assert.equal(await page.locator('[name=my_rating]').inputValue(),'9.0');
 assert(await page.locator('[name=favorite]').isChecked());
 assert.equal(await page.locator('[name=played_date]').inputValue(),'2026-10-05');
 await go('/search');await page.locator('.discovery-search [name=q]').fill('Portal');
 await page.locator('.suggestion-list [role=option]').first().waitFor();
 await page.locator('.suggestion-list [role=option]').first().tap();
 await page.waitForURL('**/game/123?**');
 await go('/search?q=Valve&type=developers');await page.locator('.game-card').first().tap();
 await page.waitForURL('**/search?**company=1**');assert.equal(await page.locator('.game-card').count(),3);
 await go('/set-language/tr');await go('/');
 await page.screenshot({path:'.qa/android-library-tr.png',fullPage:true});
 await go('/edit/123');await page.screenshot({path:'.qa/android-edit-tr.png',fullPage:true});
 await go('/settings');await page.screenshot({path:'.qa/android-settings-tr.png',fullPage:true});
 assert.equal(await page.locator('input[name=api_key]').count(),0);
 assert.deepEqual(errors,[]);await browser.close();
 console.log(`${checks} bilingual mobile/tablet page checks; touch add, duplicate prevention, note/rating/favorite/date, delete/Undo order, suggestions and developer navigation passed.`);
})().catch(e=>{console.error(e);process.exit(1)});
