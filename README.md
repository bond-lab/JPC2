# JPC2
Project Activity 2

**Final Deadline** June 30, 2026
 * upload report (PDF)
 * code and data
 * notes on how to run the code

## Plan for this semester

*in which our sins come back to haunt us*

We will continue with some of the tasks from last year, and also try
something new.

### Approach

* We will work in teams (4x1--2) 
* Most weeks, I will meet each team for 30 minutes in my office (3.22) 
    * I will give you more scaffolding
      
| Time         | Group    | People |
|--------------|----------|--------|
| 12:45–13:15  | Wordnet  | Dominik, Vojtěch  |
| 13:15–13:45  | WSD      | Vira   |
| 13:45–14:15  | LCM      | Barbora, Lea Karolina  |
| 14:15–14:45  | Metaphor | Zuzana   |


* Once every 4 weeks, you will prepare a 20-minute presentation to the other teams (in 2.05).
  * On Tue April the 16th, we will not have a meeting
  * On Tue April the 23rd, we will meet in the morning 10am wordnet, 10:30 WSD, 11:00 LCM, 11:30 Metaphor. 
  * Next presentation Apr 30

### Tasks

* WSD --- we got some nice results for models, and have a good evaluation script.  
  * Vira
  * There is a server accessible.
  * create a test harness to test improvements
  * run with different contexts and models
  * try to fix the MWE problem


Most programming

* LCM --- we did not make much progress, let's try again
  * extract known Conceptual Metaphors
  * try to map to conceptual metaphors map using hypernyms
      

* Metaphor Quality control
  * Jakub, Zuzana	
  * use either lexical conceptual mappings or make up your own
  * use top down patterns to predict metaphor
  * look at errors (could be real differences)
	

Most linguistics

* [Wordnet Quality Control](https://github.com/omwn/omwn.github.io/discussions/10) (for all languages in OMW)
  * Dominik, Vojtěch
  * make merged wordnet with reduced graph <https://gwc2014.ut.ee/proceedings_of_GWC_2014.pdf#page=128>
  * merge in TUFS wordnets
  * map lemmas to examples (mainly done in CygNet) <https://github.com/rowanhm/cygnet>
 	* Japanese --- also try to add missing
  * try to mark lexicalization

Most multilingual

## Tasks
* by 02-17 finalize groups, 
* Make task README.md
* write task description, outline next steps

## Final Write up

Write a short (6-10 page) paper in LaTeX, describing what you did, how you did it, what problems you had and what remains to be done.  References and appendices don't count toward the page total.   Upload the paper in LaTeX and PDF, along with all all code and any data you created (e.g. for evaluations) to github.

I give a rough example in <https://github.com/bond-lab/JPC1/tree/main/tasks/wordnet>.  it is slightly too long, I should make some graphs smaller.


### Structure of paper

* Title, authors, contact, date, class (Top of first page)

* Introduction: what are you trying to do and why, has anyone else worked on this before (2-3p)

* Method:  How are you solving the problem, what is your approach (1-3 p)

* Results and Evaluation: What are your results, how well did you do  (1-3 p)
    * you should have some comparison to a human test set (you can make it)
	* you should give numerical results --- how many analyzed, what result for what approach

* Discussion: (1-3 p)
    * what approach worked best
	* what did you try that is new
	* what would you like to try but couldn't

* Conclusions (0.5p)
    * summary of what you did, what your results were, what remains to be done.  Someone should be able to read this without reading the whole paper 
	
* References

* Appendices (optional)
    * If there are more details you want to go into, but didn't have room.  The paper should be  understandable without reading the appendices
	
	
### Structure of files

You should have a `README.md` that lists all the files and explains how to run your code.  If it requires other modules, list them in `requirements.txt`.  

